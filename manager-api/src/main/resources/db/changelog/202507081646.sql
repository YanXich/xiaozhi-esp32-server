-- 设备工厂表
CREATE TABLE device_factory (
  id bigint NOT NULL AUTO_INCREMENT COMMENT 'id',
  name varchar(255) NOT NULL COMMENT '工厂名称',
  code varchar(50) NOT NULL COMMENT '工厂编号',
  country varchar(100) NOT NULL COMMENT '国家',
  status varchar(20) NOT NULL COMMENT '状态(ACTIVE:启用, INACTIVE:停用)',
  PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='设备工厂表';

-- 设备生产批次表
CREATE TABLE device_production_batch (
  id varchar(32) NOT NULL COMMENT 'id',
  factory_id bigint NOT NULL COMMENT '工厂ID',
  model_type varchar(50) NOT NULL COMMENT '型号',
  production_date varchar(20) NOT NULL COMMENT '生产日期',
  hardware_version varchar(50) NOT NULL COMMENT '硬件版本',
  agent_code varchar(50) NOT NULL COMMENT '代理编码',
  status varchar(20) NOT NULL COMMENT '状态(PENDING:待生产, IN_PROGRESS:生产中, COMPLETED:已生产, CANCELLED:作废)',
  create_date datetime COMMENT '创建时间',
  update_date datetime COMMENT '更新时间',
  PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='设备生产批次表';

-- 设备号表
CREATE TABLE device_number (
  id varchar(32) NOT NULL COMMENT 'id',
  batch_id varchar(32) NOT NULL COMMENT '批次ID',
  device_number varchar(20) NOT NULL COMMENT '设备号',
  status varchar(20) NOT NULL COMMENT '状态(INITIALIZED:初始化, GENERATED:已生成, BOUND:已绑定)',
  create_date datetime COMMENT '创建时间',
  update_date datetime COMMENT '更新时间',
  PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='设备号表';

-- 设备MAC地址表
CREATE TABLE device_mac (
  id varchar(32) NOT NULL COMMENT 'id',
  device_number varchar(20) NOT NULL COMMENT '设备号',
  mac_address varchar(50) NOT NULL COMMENT 'MAC地址',
  car_model varchar(50) COMMENT '车型',
  user_id bigint COMMENT '用户ID',
  status varchar(20) NOT NULL COMMENT '状态(UNUSED:未使用, USED:已使用)',
  create_date datetime COMMENT '创建时间',
  update_date datetime COMMENT '更新时间',
  PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='设备MAC地址表';