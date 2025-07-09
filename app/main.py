from app.routers import leisure_sports
from app.routers import travel_plans
app.include_router(leisure_sports.router)
app.include_router(travel_plans.router)
