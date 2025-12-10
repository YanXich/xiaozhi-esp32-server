-- 车型配置表
CREATE TABLE device_car_model (
  id varchar(32) NOT NULL COMMENT '车型ID',
  description varchar(255) NOT NULL COMMENT '车型描述（如：宝马X5）',
  command_config json NOT NULL COMMENT '车型命令配置（JSON格式存储）',
  create_date datetime COMMENT '创建时间',
  update_date datetime COMMENT '更新时间',
  PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='车型配置表';