package xiaozhi.modules.device.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;

import java.util.Date;

@Data
@TableName("device_production_batch")
public class DeviceProductionBatchEntity {
    @TableId(type = IdType.AUTO)
    private Long id;
    
    private Long factoryId;
    
    private String modelType;
    
    private String productionDate;
    
    private String hardwareVersion;
    
    private String agentCode;
    
    // 修改为Integer类型，对应数据库tinyint
    private Integer status;
    
    // 添加开始序号和结束序号字段
    private Integer startSerialNumber;
    
    private Integer endSerialNumber;
    
    @TableField(fill = FieldFill.INSERT)
    private Date createDate;
    
    @TableField(fill = FieldFill.UPDATE)
    private Date updateDate;
    
    // 删除原有的枚举类，因为状态现在存储为数字
}