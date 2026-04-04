import requests
import re
from datetime import datetime
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "에이린 선생님의 최종 처방전! 이제 마파두부 덮밥이 보일 거야!"}

@app.get("/meal")
def get_meal(date: str = None):
    # 1. 날짜 설정 (안 적으면 오늘, 적으면 그 날짜)
    if not date:
        date = datetime.now().strftime("%Y%m%d")
    
    # 2. 🛡️ 학교 코드 수정 (네가 성공했던 바로 그 코드: 7530554)
    url = "https://open.neis.go.kr/hub/mealServiceDietInfo"
    params = {
        "Type": "json",
        "ATPT_OFCDC_SC_CODE": "J10", # 경기도 교육청
        "SD_SCHUL_CODE": "7530554",  # ⭐ 여기가 핵심! 네가 성공했던 코드로 바꿨어!
        "MLSV_YMD": date
    }
    
    response = requests.get(url, params=params)
    data = response.json()
    
    # 3. 데이터가 있는지 확인하고 예쁘게 다듬기
    try:
        # 급식 데이터 뭉치 가져오기
        meals_row = data["mealServiceDietInfo"][1]["row"]
        
        result_meals = {}
        for row in meals_row:
            meal_type = row["MMEAL_SC_NM"] # 조식, 중식, 석식
            
            # 지저분한 메뉴 이름 다듬기 (마파두부덮밥5.6... -> 마파두부덮밥)
            raw_menu = row["DDISH_NM"]
            clean_menu = []
            for item in raw_menu.split("<br/>"):
                # 숫자, 마침표, 괄호를 지우고 글자만 남김
                food = re.sub(r'[0-9\.\(\)]', '', item).strip()
                if food:
                    clean_menu.append(food)
            
            result_meals[meal_type] = {
                "menu": clean_menu,
                "calories": row["CAL_INFO"]
            }
            
        return {
            "success": True,
            "school": "대평고등학교",
            "date": date,
            "meals": result_meals
        }
        
    except:
        # 데이터가 없을 때의 친절한 설명
        return {
            "success": False,
            "message": "급식 데이터를 찾을 수 없어. 날짜를 확인해줘!",
            "debug_data": data # 뭐가 문제인지 원본 데이터 보여주기
        }

# 학교 찾기 기능도 혹시 모르니 아래에 붙여둘게!
@app.get("/find_school")
def find_school(name: str):
    url = "https://open.neis.go.kr/hub/schoolInfo"
    params = {"Type": "json", "SCHUL_NM": name}
    try:
        response = requests.get(url, params=params).json()
        schools = response["schoolInfo"][1]["row"]
        return [{"학교이름": s["SCHUL_NM"], "교육청코드": s["ATPT_OFCDC_SC_CODE"], "학교코드": s["SD_SCHUL_CODE"]} for s in schools]
    except:
        return {"error": "학교를 찾을 수 없습니다."}


@app.get("/weather")
def get_weather():
    # 1. 수원(Suwon) 날씨 정보를 JSON 형태로 주는 마법의 주소야.
    # 인증키 없이도 쓸 수 있어서 아주 간편하단다!
    url = "https://wttr.in/Suwon?format=j1"
    
    try:
        response = requests.get(url)
        data = response.json()
        
        # 2. 복잡한 데이터 속에서 '현재 날씨' 부분만 쏙 빼내기
        current = data["current_condition"][0]
        
        temp_c = current["temp_C"]        # 현재 온도 (섭씨)
        weather_desc = current["lang_ko"][0]["value"] if "lang_ko" in current else current["weatherDesc"][0]["value"] # 날씨 상태 (맑음, 흐림 등)
        humidity = current["humidity"]    # 습도
        feels_like = current["FeelsLikeC"] # 체감 온도
        
        # 3. 에이린 선생님의 특별 처방 (날씨에 따른 조언)
        # 나중에 유니티 앱 화면 하단에 띄워주면 아주 센스 있겠지?
        advice = "오늘도 활기찬 학교 생활 보내렴!"
        temp_int = int(temp_c)
        
        if "Rain" in current["weatherDesc"][0]["value"] or "Shower" in current["weatherDesc"][0]["value"]:
            advice = "비 소식이 있어! 우산을 꼭 챙기렴. ☔"
        elif temp_int < 5:
            advice = "날씨가 아주 춥구나. 따뜻하게 입고 가야 해! 🧣"
        elif temp_int > 28:
            advice = "날씨가 많이 덥네. 물을 자주 마시렴! 💧"

        # 4. 유니티 친구에게 줄 예쁜 봉투에 담기
        return {
            "success": True,
            "location": "Suwon",
            "current_temp": f"{temp_c}°C",
            "feels_like": f"{feels_like}°C",
            "condition": weather_desc,
            "humidity": f"{humidity}%",
            "doctor_advice": advice
        }

    except Exception as e:
        return {
            "success": False,
            "message": "날씨 정보를 가져오는 데 실패했어.",
            "error": str(e)
        }