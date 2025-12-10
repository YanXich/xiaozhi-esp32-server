package xiaozhi.modules.device.dto;

import lombok.Data;

@Data
public class DeviceProductionBatchDTO {
    private Long factoryId;
    private String status; // 待生产, 生产中, 已生产, 作废
    private String modelType;
    private String productionDate;
    private String hardwareVersion;
    private String agentCode;

    
    // 添加开始序号和结束序号字段
    private Integer startSerialNumber;
    
    private Integer endSerialNumber;
    
    // 添加查询用的字段
    private String startDate; // 开始日期查询
    private String endDate;   // 结束日期查询
    
    // 添加分页字段
    private Integer page = 1; // 页码
    private Integer limit = 10; // 每页数量
}