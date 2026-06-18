"""
Study-00 · 위성영상 한 장 띄우기
원격탐사 연구자의 '첫 바이브 코딩' 결과물.
Claude Code에게 일상 언어로 시켜서 만든 가장 작은 스크립트입니다.
"""

import ee
import geemap

# 1) Earth Engine 인증 + 초기화
#    처음 한 번은 브라우저가 열려 로그인을 요청합니다.
ee.Authenticate()
ee.Initialize()

# 2) 관심 지역(AOI): 서울 부근의 한 점
seoul = ee.Geometry.Point([127.0, 37.5])

# 3) Sentinel-2 위성영상 중 '구름 적고 최근' 한 장 고르기
image = (
    ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
    .filterBounds(seoul)                                   # 서울을 덮는 영상만
    .filterDate("2024-01-01", "2024-12-31")                # 2024년 안에서
    .sort("CLOUDY_PIXEL_PERCENTAGE")                       # 구름 적은 순으로 정렬
    .first()                                               # 가장 맑은 한 장
)

# 4) 자연색(RGB)으로 보이게 설정
#    B4=빨강, B3=초록, B2=파랑. 0~3000 범위를 0~1로 펴서 보기 좋게.
vis = {"bands": ["B4", "B3", "B2"], "min": 0, "max": 3000}

# 5) 지도에 띄우기
m = geemap.Map(center=[37.5, 127.0], zoom=11)
m.add_layer(image, vis, "Sentinel-2 (가장 맑은 한 장)")
m.add_layer(seoul, {"color": "red"}, "관심 지점")

# 주피터/코랩에서는 아래 m 이 지도를 보여줍니다.
# 스크립트로 실행할 땐 HTML로 저장해 브라우저로 엽니다.
m.to_html("study00_map.html")
print("지도를 study00_map.html 로 저장했어요. 브라우저로 열어보세요.")
print("(주피터/코랩이라면 마지막 줄에 m 만 적어도 지도가 보입니다.)")
