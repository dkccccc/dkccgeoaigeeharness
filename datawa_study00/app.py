"""
datawa_study00 · 위성영상 한 장 띄우는 웹앱 (구글맵 스타일 UI)
서울을 '온전히 덮는' 가장 최신 Sentinel-2 한 장을, 서울 영역만 잘라 PNG 한 장으로 받아 올린다.
(타일 수십 개 대신 이미지 1장 → 서비스계정 할당량 throttle 없이 한 번에 다 뜸)
실행:  streamlit run app.py  (처음 한 번 earthengine authenticate)
"""

from datetime import date, timedelta

import ee
import folium
import streamlit as st
import streamlit.components.v1 as components

try:
    ee.Initialize()
except Exception:
    ee.Authenticate()
    ee.Initialize()


def google_basemap(fmap, lyrs, name):
    folium.TileLayer(tiles=f"https://mt1.google.com/vt/lyrs={lyrs}&x={{x}}&y={{y}}&z={{z}}",
                     attr="Google", name=name, overlay=False, control=True, max_zoom=20).add_to(fmap)


st.set_page_config(page_title="위성영상", layout="wide")

st.markdown("""
<style>
  header[data-testid="stHeader"] {display:none;}
  footer {display:none;}
  .block-container {padding:0 !important; max-width:100% !important;}
  [data-testid="stMainBlockContainer"] {padding:0 !important;}
  [data-testid="stVerticalBlock"] {gap:0 !important;}
  iframe {display:block; border:0; height:100vh !important; width:100% !important;}
</style>
""", unsafe_allow_html=True)


@st.cache_data(ttl=1800, show_spinner="위성영상 불러오는 중...")
def load_scene():
    W, S, E, N = 126.76, 37.42, 127.18, 37.64
    aoi = ee.Geometry.Rectangle([W, S, E, N])
    today = date.today()
    coll = (ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED").filterBounds(aoi)
            .filterDate(str(today - timedelta(days=180)), str(today + timedelta(days=1)))
            .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 40)))
    scene = (coll.filter(ee.Filter.contains(leftField=".geo", rightValue=aoi))
             .sort("system:time_start", False).first())
    thumb = scene.clip(aoi).getThumbURL({
        "bands": ["B4", "B3", "B2"], "min": 0, "max": 3000,
        "dimensions": 2560, "region": aoi, "format": "png",
    })
    return {
        "thumb": thumb,
        "date": ee.Date(scene.get("system:time_start")).format("YYYY-MM-dd").getInfo(),
        "cloud": scene.get("CLOUDY_PIXEL_PERCENTAGE").getInfo() or 0.0,
        "tile": scene.get("MGRS_TILE").getInfo(),
        "sat": scene.get("SPACECRAFT_NAME").getInfo(),
        "bounds": [[S, W], [N, E]],
    }


info = load_scene()
center = [(info["bounds"][0][0] + info["bounds"][1][0]) / 2,
          (info["bounds"][0][1] + info["bounds"][1][1]) / 2]

m = folium.Map(location=center, tiles=None, control_scale=True)
google_basemap(m, "m", "Google 지도")
folium.raster_layers.ImageOverlay(
    image=info["thumb"], bounds=info["bounds"], opacity=1.0,
    name=f"Sentinel-2 ({info['date']})",
).add_to(m)
folium.LayerControl(collapsed=True).add_to(m)

card = f"""
<div style="position:fixed; top:12px; left:60px; z-index:9999; background:#fff;
            padding:10px 14px; border-radius:10px; box-shadow:0 1px 6px rgba(0,0,0,.35);
            font-family:'Malgun Gothic',sans-serif; font-size:13px; line-height:1.6; color:#222;">
  <div style="font-weight:700; font-size:15px; margin-bottom:2px;">🛰️ 위성영상 한 장 (서울)</div>
  <div>촬영일 <b>{info['date']}</b> · {info['sat']}</div>
  <div>타일 {info['tile']} · 구름 {info['cloud']:.1f}%</div>
</div>
"""
m.get_root().html.add_child(folium.Element(card))
m.fit_bounds(info["bounds"])

components.html(m.get_root().render(), height=900)
