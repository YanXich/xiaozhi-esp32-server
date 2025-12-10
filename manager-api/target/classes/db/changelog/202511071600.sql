-- 步骤1：删除原主键约束（因类型变更需先移除）
ALTER TABLE device_production_batch DROP PRIMARY KEY;

-- 步骤2：修改id字段类型为bigint（非空）
ALTER TABLE device_production_batch 
MODIFY COLUMN id bigint NOT NULL COMMENT 'id';

-- 步骤3：重新设置id为主键，并添加自增属性
ALTER TABLE device_production_batch 
ADD PRIMARY KEY (id),
MODIFY COLUMN id bigint NOT NULL AUTO_INCREMENT COMMENT 'id';

-- 步骤1：删除原主键约束
ALTER TABLE device_number DROP PRIMARY KEY;

-- 步骤2：修改id字段类型为bigint（非空）
ALTER TABLE device_number 
MODIFY COLUMN id bigint NOT NULL COMMENT 'id';

-- 步骤3：重新设置id为主键，并添加自增属性
ALTER TABLE device_number 
ADD PRIMARY KEY (id),
MODIFY COLUMN id bigint NOT NULL AUTO_INCREMENT COMMENT 'id';

ALTER TABLE device_number 
MODIFY COLUMN batch_id bigint NOT NULL COMMENT '批次ID';

-- 步骤1：删除原主键约束
ALTER TABLE device_car_model DROP PRIMARY KEY;

-- 步骤2：修改id字段类型为bigint（非空）
ALTER TABLE device_car_model 
MODIFY COLUMN id bigint NOT NULL COMMENT 'id';

-- 步骤3：重新设置id为主键，并添加自增属性
ALTER TABLE device_car_model 
ADD PRIMARY KEY (id),
MODIFY COLUMN id bigint NOT NULL AUTO_INCREMENT COMMENT 'id';

-- 步骤1：删除原主键约束
ALTER TABLE device_mac DROP PRIMARY KEY;

-- 步骤2：修改id字段类型为bigint（非空）
ALTER TABLE device_mac 
MODIFY COLUMN id bigint NOT NULL COMMENT 'id';

-- 步骤3：重新设置id为主键，并添加自增属性
ALTER TABLE device_mac 
ADD PRIMARY KEY (id),
MODIFY COLUMN id bigint NOT NULL AUTO_INCREMENT COMMENT 'id';