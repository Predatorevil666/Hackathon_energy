-- Создание таблицы contacts для хранения контактных данных
CREATE TABLE IF NOT EXISTS contacts (
    id SERIAL PRIMARY KEY,
    account_id INTEGER NOT NULL,
    phone VARCHAR(20),
    email VARCHAR(255),
    url1 VARCHAR(512),
    url2 VARCHAR(512),
    comment TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Индекс для быстрого поиска по account_id (основной поиск)
CREATE INDEX IF NOT EXISTS idx_contacts_account_id ON contacts(account_id);

-- Индексы для поиска по контактным данным
CREATE INDEX IF NOT EXISTS idx_contacts_phone ON contacts(phone);
CREATE INDEX IF NOT EXISTS idx_contacts_email ON contacts(email);

-- Триггер для автоматического обновления updated_at при изменении записи
CREATE OR REPLACE FUNCTION update_modified_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_contacts_modtime
BEFORE UPDATE ON contacts
FOR EACH ROW
EXECUTE FUNCTION update_modified_column();

-- Комментарии к таблице и полям для документации
COMMENT ON TABLE contacts IS 'Контактные данные, собранные с помощью OSINT';
COMMENT ON COLUMN contacts.account_id IS 'ID аккаунта потребителя энергии';
COMMENT ON COLUMN contacts.phone IS 'Номер телефона';
COMMENT ON COLUMN contacts.email IS 'Электронная почта';
COMMENT ON COLUMN contacts.url1 IS 'Основной URL контакта';
COMMENT ON COLUMN contacts.url2 IS 'Дополнительный URL контакта';
COMMENT ON COLUMN contacts.comment IS 'Комментарий или дополнительная информация';