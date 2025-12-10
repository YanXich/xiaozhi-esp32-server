package xiaozhi.modules.device.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;

import java.util.Date;

@Data
@TableName("device_mac")
public class DeviceMacEntity {
    @TableId(type = IdType.AUTO)
    private Long id;
    
    private String deviceNumber;
    
    private String macAddress;
    
    private String carModel;
    
    private Long userId;
    
    // 新增设备名称字段
    private String deviceName;
    
    // 新增备注字段
    private String remark;
    
    // 修改为Integer类型，对应数据库tinyint
    private Integer status;
    
    @TableField(fill = FieldFill.INSERT)
    private Date createDate;
    
    @TableField(fill = FieldFill.UPDATE)
    private Date updateDate;
}