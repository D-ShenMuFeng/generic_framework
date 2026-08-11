from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(tags=["test接口"], prefix="/test")

@router.post("/test")
async def get_food_list():
    return {
        "code": 1,
        "msg": "查询成功",
        "data": ''
    }