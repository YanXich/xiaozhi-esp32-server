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
    // 修改: 处理maxSerialNumber为null的情况，默认为0
    if (maxSerialNumber == null) {
        maxSerialNumber = 0;
    }
    if (dto.getStartSerialNumber() <= maxSerialNumber) {
        return new Result<DeviceProductionBatchEntity>().error("开始序号必须大于当前最大序号(" + maxSerialNumber + ") + 1，即必须大于" + (maxSerialNumber + 1));
    }