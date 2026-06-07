import requests
import re
from datetime import datetime
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI()

# ---------------------------------------------------------
# 🌐 CORS 설정 (유니티나 웹에서 API 호출할 때 차단되지 않게 함)
# ---------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # 모든 접근 허용 (실제 배포때는 특정 도메인만 넣어도 됨)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------
# ⚙️ 전역 변수 설정 (앱 상태 및 임시 DB)
# ---------------------------------------------------------
CURRENT_APP_VERSION = "1.0.0" # 현재 최신 앱 버전
MIN_REQ_VERSION = "1.0.0"     # 이 버전보다 낮으면 앱 실행 막음
IS_MAINTENANCE = False        # 🚨 이 값을 True로 바꾸고 Render에서 재시작하면 앱 차단됨!
MAINTENANCE_MSG = "현재 서버 업데이트 중입니다. 잠시만 기다려주세요! 🛠️"

# 별점을 임시로 저장할 딕셔너리 (Render가 재시작되면 초기화됨. 나중에 진짜 DB로 변경 추천!)
meal_ratings_db = {}


# ---------------------------------------------------------
# 1️⃣ 기본 엔드포인트
# ---------------------------------------------------------
@app.get("/")
def read_root():
    return {"message": "절대이사이트에들어오지마"}


# ---------------------------------------------------------
# 2️⃣ [앱 컨트롤 타워] 유지보수 및 업데이트 관리 API
# ---------------------------------------------------------
@app.get("/status")
def get_app_status():
    """
    유니티 앱이 켜질 때 가장 먼저 호출해야 하는 API.
    버전 체크와 서버 점검 상태를 알려줌.
    """
    return {
        "success": True,
        "latest_version": CURRENT_APP_VERSION,
        "min_version": MIN_REQ_VERSION,
        "is_maintenance": IS_MAINTENANCE,
        "maintenance_message": MAINTENANCE_MSG,
        "notice": "이번 주 금요일 동아리 발표가 있습니다! 🎉" # 앱 메인에 띄울 공지사항
    }


# ---------------------------------------------------------
# 3️⃣ 급식 조회 API
# ---------------------------------------------------------
@app.get("/meal")
def get_meal(date: str = None):
    # 날짜 설정 (안 적으면 오늘, 적으면 그 날짜)
    if not date:
        date = datetime.now().strftime("%Y%m%d")
    
    # NEIS API 설정
    url = "https://open.neis.go.kr/hub/mealServiceDietInfo"
    params = {
        "Type": "json",
        "ATPT_OFCDC_SC_CODE": "J10", # 경기도 교육청
        "SD_SCHUL_CODE": "7530554",  # 대평고등학교 코드
        "MLSV_YMD": date
    }
    
    try:
        response = requests.get(url, params=params)
        data = response.json()
        
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
        
    except Exception as e:
        return {
            "success": False,
            "message": "급식 데이터를 찾을 수 없어. 쉬는 날이거나 날짜를 확인해줘!",
            "error": str(e)
        }


# ---------------------------------------------------------
# 4️⃣ 학교 찾기 API
# ---------------------------------------------------------
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


# ---------------------------------------------------------
# 5️⃣ 날씨 API
# ---------------------------------------------------------
@app.get("/weather")
def get_weather():
    url = "https://wttr.in/Suwon?format=j1"
    
    try:
        response = requests.get(url)
        data = response.json()
        
        current = data["current_condition"][0]
        temp_c = current["temp_C"]
        weather_desc = current["lang_ko"][0]["value"] if "lang_ko" in current else current["weatherDesc"][0]["value"]
        humidity = current["humidity"]
        feels_like = current["FeelsLikeC"]
        
        # 에이린 선생님의 특별 처방
        advice = "오늘도 활기찬 학교 생활!"
        temp_int = int(temp_c)
        
        if "Rain" in current["weatherDesc"][0]["value"] or "Shower" in current["weatherDesc"][0]["value"]:
            advice = "비 소식이 있어! 우산을 꼭 챙겨. ☔"
        elif temp_int < 5:
            advice = "날씨가 아주 추우니, 따뜻하게 입고 가야 해. 🧣"
        elif temp_int > 28:
            advice = "날씨가 많이 덥네. 물을 자주 마셔. 💧"

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


# ---------------------------------------------------------
# 6️⃣ [참여형 기능] 급식 별점 시스템 (POST, GET)
# ---------------------------------------------------------
# 유니티에서 보낼 데이터의 형식을 정의
class Rating(BaseModel):
    date: str   # 예: "20260607"
    score: int  # 1 ~ 5 별점

@app.post("/meal/rating")
def add_meal_rating(rating: Rating):
    """유니티에서 별점을 서버로 보낼 때 사용하는 API"""
    if rating.date not in meal_ratings_db:
        meal_ratings_db[rating.date] = []
        
    meal_ratings_db[rating.date].append(rating.score)
    
    total_votes = len(meal_ratings_db[rating.date])
    avg_score = sum(meal_ratings_db[rating.date]) / total_votes
    
    return {
        "success": True,
        "message": "별점이 성공적으로 반영되었어!",
        "date": rating.date,
        "average_score": round(avg_score, 1),
        "total_votes": total_votes
    }

@app.get("/meal/rating")
def get_meal_rating(date: str):
    """유니티에서 특정 날짜의 평균 별점을 물어볼 때 사용하는 API"""
    if date in meal_ratings_db and len(meal_ratings_db[date]) > 0:
        avg_score = sum(meal_ratings_db[date]) / len(meal_ratings_db[date])
        return {
            "success": True,
            "date": date,
            "average_score": round(avg_score, 1),
            "total_votes": len(meal_ratings_db[date])
        }
    else:
        # 아직 투표가 없는 경우
        return {
            "success": True,
            "date": date, 
            "average_score": 0.0, 
            "total_votes": 0
        }
