package xiaozhi.modules.device.controller;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.AllArgsConstructor;
import org.springframework.web.bind.annotation.*;
import xiaozhi.common.utils.Result;
import xiaozhi.modules.device.dto.DeviceFactoryDTO;
import xiaozhi.modules.device.dto.DeviceNumberGenerateDTO;
import xiaozhi.modules.device.dto.DeviceProductionBatchDTO;
import xiaozhi.modules.device.dto.DeviceFactoryQueryDTO;
import xiaozhi.modules.device.dto.DeviceCarModelDTO;
import xiaozhi.modules.device.entity.DeviceFactoryEntity;
import xiaozhi.modules.device.entity.DeviceProductionBatchEntity;
import xiaozhi.modules.device.entity.DeviceNumberEntity;
import xiaozhi.modules.device.entity.DeviceCarModelEntity;
import xiaozhi.modules.device.service.DeviceFactoryService;
import xiaozhi.modules.device.service.DeviceNumberService;
import xiaozhi.modules.device.service.DeviceProductionBatchService;
import xiaozhi.modules.device.service.DeviceCarModelService;
import xiaozhi.modules.device.service.DeviceMacService;
import xiaozhi.modules.device.entity.DeviceMacEntity;
import xiaozhi.common.page.PageData;
import xiaozhi.common.constant.Constant;
import xiaozhi.common.validator.ValidatorUtils;
import java.util.List;
import java.util.Map;
import java.util.ArrayList;

import lombok.extern.slf4j.Slf4j;

@Tag(name = "设备管理")
@RestController
@RequestMapping("/device-management")
@AllArgsConstructor
@Slf4j
public class DeviceManagementController {
    
    private final DeviceFactoryService deviceFactoryService;
    private final DeviceProductionBatchService deviceProductionBatchService;
    private final DeviceNumberService deviceNumberService;
    private final DeviceCarModelService deviceCarModelService;
    private final DeviceMacService deviceMacService;
    
    @PostMapping("/factory")
    @Operation(summary = "创建工厂")
    public Result<DeviceFactoryEntity> createFactory(@RequestBody DeviceFactoryDTO dto) {
        DeviceFactoryEntity entity = new DeviceFactoryEntity();
        entity.setName(dto.getName());
        entity.setCode(dto.getCode());
        entity.setCountry(dto.getCountry());
        entity.setStatus(0); // 默认启用状态，0表示启用(对应tinyint)
        deviceFactoryService.insert(entity);
        return new Result<DeviceFactoryEntity>().ok(entity);
    }
    
    @PutMapping("/factory/{id}")
    @Operation(summary = "更新工厂")
    public Result<DeviceFactoryEntity> updateFactory(@PathVariable Long id, @RequestBody DeviceFactoryDTO dto) {
        DeviceFactoryEntity entity = deviceFactoryService.selectById(id);
        if (entity == null) {
            return new Result<DeviceFactoryEntity>().error("工厂不存在");
        }
        entity.setName(dto.getName());
        entity.setCode(dto.getCode());
        entity.setCountry(dto.getCountry());
        deviceFactoryService.updateById(entity);
        return new Result<DeviceFactoryEntity>().ok(entity);
    }
    
    @GetMapping("/factories")
    @Operation(summary = "查询工厂列表")
    public Result<PageData<DeviceFactoryEntity>> queryFactories(DeviceFactoryQueryDTO queryDTO) {
        PageData<DeviceFactoryEntity> pageData = deviceFactoryService.queryFactories(queryDTO);
        return new Result<PageData<DeviceFactoryEntity>>().ok(pageData);
    }
    
    @PostMapping("/batch")
    @Operation(summary = "创建生产批次")
    public Result<DeviceProductionBatchEntity> createBatch(@RequestBody DeviceProductionBatchDTO dto) {
        // 序号校验： StartSerialNumber > max() + 1, StartSerialNumber < EndSerialNumber, StartSerialNumber和EndSerialNumber不能为空
        if (dto.getStartSerialNumber() == null || dto.getEndSerialNumber() == null) {
            return new Result<DeviceProductionBatchEntity>().error("开始序号和结束序号不能为空");
        }
        
        if (dto.getStartSerialNumber() >= dto.getEndSerialNumber()) {
            return new Result<DeviceProductionBatchEntity>().error("开始序号必须小于结束序号");
        }
        
        // 获取该工厂下最大的序号
        Integer maxSerialNumber = deviceProductionBatchService.getMaxSerialNumber(dto.getFactoryId());
        if (dto.getStartSerialNumber() <= maxSerialNumber) {
            return new Result<DeviceProductionBatchEntity>().error("开始序号必须大于当前最大序号(" + maxSerialNumber + ") + 1，即必须大于" + (maxSerialNumber + 1));
        }

        // 获取工厂信息
        DeviceFactoryEntity factory = deviceFactoryService.selectById(dto.getFactoryId());
        if (factory == null) {
            return new Result<DeviceProductionBatchEntity>().error("工厂不存在");
        }

        // 实体构造
        DeviceProductionBatchEntity entity = new DeviceProductionBatchEntity();
        entity.setFactoryId(dto.getFactoryId());
        entity.setModelType(dto.getModelType());
        entity.setProductionDate(dto.getProductionDate());
        entity.setHardwareVersion(dto.getHardwareVersion());
        entity.setAgentCode(dto.getAgentCode());
        entity.setStatus(0); // 0表示待生产(对应tinyint)
        
        // 设置开始序号和结束序号
        entity.setStartSerialNumber(dto.getStartSerialNumber());
        entity.setEndSerialNumber(dto.getEndSerialNumber());
        
        deviceProductionBatchService.insert(entity);

        /*
        * 设备号生成规则：
        * 国家号： 2位， 86
        * 厂家: 3位， 006
        * 代理商： 3位， 028
        * 年： 2位， 25
        * 月： 2位. 10，
        * 机型: 2位， 04，
        * 硬件版本： 2位， 11
        * 生产序号： 7位， 0000001
        */
        String productionDate = entity.getProductionDate();
        String year = productionDate.substring(2, 4); // 取年份后两位
        String month = productionDate.substring(5, 7); // 取月份
        String country = String.format("%02d", Integer.parseInt(factory.getCountry())); // 国家号2位
        String factoryCode = String.format("%03d", factory.getId()); // 厂家3位
        String agentCode = String.format("%03d", Integer.parseInt(entity.getAgentCode())); // 代理商3位
        String modelType = String.format("%02d", Integer.parseInt(entity.getModelType())); // 机型2位
        String hardwareVersion = String.format("%02d", Integer.parseInt(entity.getHardwareVersion())); // 硬件版本2位
        String deviceNumberBase = country + factoryCode + agentCode + year + month + modelType + hardwareVersion;

        // 设备号生成， 从startSerialNumber开始，直到endSerialNumber插入生成设备号
        List<DeviceNumberEntity> deviceNumberEntities = new ArrayList<>(); // 添加设备号实体列表定义
        for (int i = entity.getStartSerialNumber(); i <= entity.getEndSerialNumber(); i++) {
            String serialNumberStr = String.format("%07d", i); // 生产序号7位
            String deviceNumber = deviceNumberBase + serialNumberStr;
            
            DeviceNumberEntity deviceNumberEntity = new DeviceNumberEntity(); // 修正变量名
            deviceNumberEntity.setBatchId(entity.getId()); // 修正batchId的设置
            deviceNumberEntity.setDeviceNumber(deviceNumber);
            deviceNumberEntity.setStatus(1); // 1表示已生成状态
            deviceNumberEntities.add(deviceNumberEntity);
        }
        
        // 批量插入设备号
        if (!deviceNumberEntities.isEmpty()) {
            // 添加调试日志，打印第一个待插入的设备号
            log.info("第一个待插入的设备号: {}", deviceNumberEntities.get(0).getDeviceNumber());
            log.info("待插入设备号总数: {}", deviceNumberEntities.size());
            deviceNumberService.saveBatch(deviceNumberEntities);
        }
        
        return new Result<DeviceProductionBatchEntity>().ok(entity);
    }
    
    @GetMapping("/batches")
    @Operation(summary = "查询生产批次列表")
    public Result<PageData<DeviceProductionBatchEntity>> queryBatches(DeviceProductionBatchDTO queryDTO) {
        PageData<DeviceProductionBatchEntity> pageData = deviceProductionBatchService.queryBatches(queryDTO);
        return new Result<PageData<DeviceProductionBatchEntity>>().ok(pageData);
    }

    @GetMapping("/device-numbers/{batchId}")
    @Operation(summary = "查询批次设备号列表")
    public Result<PageData<DeviceNumberEntity>> queryDeviceNumbers(
        @PathVariable Long batchId,
        @RequestParam(defaultValue = "1") Integer page,
        @RequestParam(defaultValue = "10") Integer limit) {
    PageData<DeviceNumberEntity> pageData = deviceNumberService.queryDeviceNumbers(batchId, page, limit);
    return new Result<PageData<DeviceNumberEntity>>().ok(pageData);
}
    
    @GetMapping("/device-numbers")
    @Operation(summary = "查询所有设备号列表")
    public Result<PageData<DeviceNumberEntity>> queryAllDeviceNumbers(
            @RequestParam(defaultValue = "1") Integer page,
            @RequestParam(defaultValue = "10") Integer limit,
            @RequestParam(defaultValue = "") String name) {
        PageData<DeviceNumberEntity> pageData = deviceNumberService.queryDeviceNumbersWithoutBatch(page, limit, name);
        return new Result<PageData<DeviceNumberEntity>>().ok(pageData);
    }
    
    @GetMapping("/export-numbers/{batchId}")
    @Operation(summary = "导出设备号为TXT")
    public Result<String> exportDeviceNumbers(@PathVariable Long batchId) {
        String content = deviceNumberService.exportDeviceNumbers(batchId);
        return new Result<String>().ok(content);
    }
        
    @PutMapping("/device-number/{id}/status/{status}")
    @Operation(summary = "更新设备号状态")
    public Result<Void> updateDeviceNumberStatus(@PathVariable Long id, @PathVariable Integer status) {
        boolean updated = deviceNumberService.updateDeviceNumberStatus(id, status);
        if (updated) {
            return new Result<Void>().ok(null);
        } else {
            return new Result<Void>().error("状态更新失败，设备号不存在");
        }
    }

    @PostMapping("/device-mac")
    @Operation(summary = "创建设备MAC")
    public Result<DeviceMacEntity> createDeviceMac(@RequestBody DeviceMacEntity deviceMac) {
        deviceMacService.insert(deviceMac);
        return new Result<DeviceMacEntity>().ok(deviceMac);
    }

    @GetMapping("/device-macs")
    @Operation(summary = "查询设备MAC列表")
    public Result<PageData<DeviceMacEntity>> queryDeviceMacs(@RequestParam Map<String, Object> params) {
        PageData<DeviceMacEntity> pageData = deviceMacService.queryDeviceMacs(params);
        return new Result<PageData<DeviceMacEntity>>().ok(pageData);
    }

    @GetMapping("/device-mac/{id}")
    @Operation(summary = "根据ID获取设备MAC")
    public Result<DeviceMacEntity> getDeviceMacById(@PathVariable Long id) {
        DeviceMacEntity deviceMac = deviceMacService.selectById(id);
        return new Result<DeviceMacEntity>().ok(deviceMac);
    }

    @PutMapping("/device-mac/{id}")
    @Operation(summary = "更新设备MAC")
    public Result<DeviceMacEntity> updateDeviceMac(@PathVariable Long id, @RequestBody DeviceMacEntity deviceMac) {
        deviceMac.setId(id);
        deviceMacService.updateById(deviceMac);
        return new Result<DeviceMacEntity>().ok(deviceMac);
    }

    @DeleteMapping("/device-mac/{id}")
    @Operation(summary = "删除设备MAC")
    public Result<Void> deleteDeviceMac(@PathVariable Long id) {
        deviceMacService.deleteById(id);
        return new Result<Void>().ok(null);
    }
    
    // @GetMapping("/device-config/{macAddress}")
    // @Operation(summary = "根据MAC地址获取设备配置")
    // public Result<Map<String, Object>> getDeviceConfigByMac(@PathVariable String macAddress) {
    //     try {
    //         Map<String, Object> result = deviceMacService.getDeviceConfigByMac(macAddress);
    //         return new Result<Map<String, Object>>().ok(result);
    //     } catch (RuntimeException e) {
    //         return new Result<Map<String, Object>>().error(e.getMessage());
    //     }
    // }
    
    @PostMapping("/car-model")
    @Operation(summary = "创建车型配置")
    public Result<DeviceCarModelEntity> createCarModel(@RequestBody DeviceCarModelDTO dto) {
        DeviceCarModelEntity entity = new DeviceCarModelEntity();
        entity.setDescription(dto.getDescription());
        entity.setCommandConfig(dto.getCommandConfig());
        deviceCarModelService.insert(entity);
        return new Result<DeviceCarModelEntity>().ok(entity);
    }
    
    @PutMapping("/car-model/{id}")
    @Operation(summary = "更新车型配置")
    public Result<DeviceCarModelEntity> updateCarModel(@PathVariable String id, @RequestBody DeviceCarModelDTO dto) {
        DeviceCarModelEntity entity = deviceCarModelService.selectById(id);
        if (entity == null) {
            return new Result<DeviceCarModelEntity>().error("车型配置不存在");
        }
        entity.setDescription(dto.getDescription());
        entity.setCommandConfig(dto.getCommandConfig());
        deviceCarModelService.updateById(entity);
        return new Result<DeviceCarModelEntity>().ok(entity);
    }
    
    @GetMapping("/car-models")
    @Operation(summary = "查询车型配置列表")
    public Result<PageData<DeviceCarModelEntity>> queryCarModels(@RequestParam Map<String, Object> params) {
        ValidatorUtils.validateEntity(params);
        PageData<DeviceCarModelEntity> pageData = deviceCarModelService.queryCarModels(params);
        return new Result<PageData<DeviceCarModelEntity>>().ok(pageData);
    }
    
    @DeleteMapping("/car-model/{id}")
    @Operation(summary = "删除车型配置")
    public Result<Void> deleteCarModel(@PathVariable Long id) {
        deviceCarModelService.delete(id);
        return new Result<>();
    }
}