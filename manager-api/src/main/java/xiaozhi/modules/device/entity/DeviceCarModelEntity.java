package xiaozhi.modules.device.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;

import java.util.Date;

@Data
@TableName("device_car_model")
public class DeviceCarModelEntity {
    @TableId(type = IdType.AUTO)
    private Long id;
    
    private String description;
    
    private String commandConfig;
    
    @TableField(fill = FieldFill.INSERT)
    private Date createDate;
    
    @TableField(fill = FieldFill.UPDATE)
    private Date updateDate;
}