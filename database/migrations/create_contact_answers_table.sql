-- contact_answers 테이블 생성
CREATE TABLE IF NOT EXISTS contact_answers (
    id SERIAL PRIMARY KEY,
    contact_id INTEGER NOT NULL UNIQUE,
    admin_id INTEGER NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    
    -- 외래키 제약조건
    CONSTRAINT fk_contact_answers_contact_id FOREIGN KEY (contact_id) 
        REFERENCES contact(id) ON DELETE CASCADE,
    CONSTRAINT fk_contact_answers_admin_id FOREIGN KEY (admin_id) 
        REFERENCES admins(admin_id) ON DELETE RESTRICT
);

-- 인덱스 생성
CREATE INDEX IF NOT EXISTS idx_contact_answer_contact_id ON contact_answers(contact_id);

-- updated_at 자동 업데이트 트리거
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_contact_answers_updated_at BEFORE UPDATE ON contact_answers
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();