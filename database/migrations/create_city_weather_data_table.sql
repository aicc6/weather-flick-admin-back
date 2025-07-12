-- Create city_weather_data table for storing weather information

CREATE TABLE IF NOT EXISTS city_weather_data (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    city_name VARCHAR NOT NULL,
    nx INTEGER NOT NULL,
    ny INTEGER NOT NULL,
    latitude DECIMAL(10, 8),
    longitude DECIMAL(11, 8),
    temperature FLOAT,
    humidity INTEGER,
    precipitation FLOAT,
    wind_speed FLOAT,
    wind_direction INTEGER,
    sky_condition VARCHAR,
    precipitation_type VARCHAR,
    weather_description VARCHAR,
    forecast_time TIMESTAMP NOT NULL,
    base_date VARCHAR,
    base_time VARCHAR,
    data_source VARCHAR DEFAULT 'KMA',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT _city_forecast_time_uc UNIQUE (city_name, forecast_time)
);

-- Create indexes
CREATE INDEX IF NOT EXISTS ix_city_weather_data_city_name ON city_weather_data(city_name);
CREATE INDEX IF NOT EXISTS ix_city_weather_data_id ON city_weather_data(id);