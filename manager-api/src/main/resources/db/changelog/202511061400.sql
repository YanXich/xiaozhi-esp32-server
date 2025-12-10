-- 为 device_factory 表新增 create_date 和 update_date 字段
ALTER TABLE device_factory
ADD COLUMN create_date datetime COMMENT '创建时间',
ADD COLUMN update_date datetime COMMENT '更新时间';

-- 为 device_mac 表新增“名称”和“备注”字段
ALTER TABLE device_mac
ADD COLUMN device_name varchar(100) COMMENT '设备名称',  -- 名称：存储设备的具体名称
ADD COLUMN remark varchar(500) COMMENT '备注信息';       -- 备注：存储设备相关的额外说明