"""create city_weather_data table

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
    # Create city_weather_data table
    op.create_table('city_weather_data',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('city_name', sa.String(), nullable=False),
        sa.Column('nx', sa.Integer(), nullable=False),
        sa.Column('ny', sa.Integer(), nullable=False),
        sa.Column('latitude', sa.DECIMAL(precision=10, scale=8), nullable=True),
        sa.Column('longitude', sa.DECIMAL(precision=11, scale=8), nullable=True),
        sa.Column('temperature', sa.Float(), nullable=True),
        sa.Column('humidity', sa.Integer(), nullable=True),
        sa.Column('precipitation', sa.Float(), nullable=True),
        sa.Column('wind_speed', sa.Float(), nullable=True),
        sa.Column('wind_direction', sa.Integer(), nullable=True),
        sa.Column('sky_condition', sa.String(), nullable=True),
        sa.Column('precipitation_type', sa.String(), nullable=True),
        sa.Column('weather_description', sa.String(), nullable=True),
        sa.Column('forecast_time', sa.DateTime(), nullable=False),
        sa.Column('base_date', sa.String(), nullable=True),
        sa.Column('base_time', sa.String(), nullable=True),
        sa.Column('data_source', sa.String(), server_default='KMA', nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('city_name', 'forecast_time', name='_city_forecast_time_uc')
    )
    op.create_index(op.f('ix_city_weather_data_city_name'), 'city_weather_data', ['city_name'], unique=False)
    op.create_index(op.f('ix_city_weather_data_id'), 'city_weather_data', ['id'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_city_weather_data_id'), table_name='city_weather_data')
    op.drop_index(op.f('ix_city_weather_data_city_name'), table_name='city_weather_data')
    op.drop_table('city_weather_data')