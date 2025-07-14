"""DEPRECATED: create city_weather_data table

This migration is deprecated. The city_weather_data table is no longer used.
Weather data is now managed in the weather_forecasts table.

Revision ID: create_city_weather_data
Revises: 
Create Date: 2025-01-13 08:25:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'create_city_weather_data'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # This table is deprecated and should not be created
    # Weather data is now stored in weather_forecasts table
    pass


def downgrade():
    # No action needed as table is not created
    pass