package xiaozhi.modules.device.dto;

import lombok.Data;

@Data
public class DeviceFactoryQueryDTO {
    private String name;      // 名称模糊查询
    private String code;      // 编号精确查询
    private String status;    // 状态查询
    private Integer page = 1; // 页码
    private Integer limit = 10; // 每页数量
}