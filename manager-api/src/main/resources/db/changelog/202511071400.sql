-- 为 device_production_batch 表新增开始序号和结束序号字段
ALTER TABLE device_production_batch
ADD COLUMN start_serial_number int COMMENT '开始序号',
ADD COLUMN end_serial_number int COMMENT '结束序号';