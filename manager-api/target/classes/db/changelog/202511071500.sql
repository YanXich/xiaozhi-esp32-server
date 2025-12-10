-- 修改 device_number 表的 device_number 字段长度为 50
ALTER TABLE device_number
MODIFY COLUMN device_number varchar(50) NOT NULL COMMENT '设备号';

-- 修改 device_mac 表的 device_number 字段长度为 50
ALTER TABLE device_mac
MODIFY COLUMN device_number varchar(50) NOT NULL COMMENT '设备号';