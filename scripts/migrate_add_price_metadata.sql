-- 已有数据库升级：decision_outcomes 增加 price_metadata
ALTER TABLE decision_outcomes ADD COLUMN IF NOT EXISTS price_metadata JSONB DEFAULT '{}';
