package xiaozhi.modules.device.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;

import java.util.Date;

@Data
@TableName("device_number")
public class DeviceNumberEntity {
    @TableId(type = IdType.AUTO)
    private Long id;
    
    private long batchId;
    
    private String deviceNumber;
    
    // 修改为Integer类型，对应数据库tinyint
    private Integer status;
    
    @TableField(fill = FieldFill.INSERT)
    private Date createDate;
    
    @TableField(fill = FieldFill.UPDATE)
    private Date updateDate;
    
    // 删除原有的枚举类，因为状态现在存储为数字
}