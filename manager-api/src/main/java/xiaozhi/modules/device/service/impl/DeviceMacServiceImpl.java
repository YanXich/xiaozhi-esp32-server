package xiaozhi.modules.device.service.impl;

import lombok.AllArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import xiaozhi.common.service.impl.BaseServiceImpl;
import xiaozhi.modules.device.dao.DeviceMacDao;
import xiaozhi.modules.device.entity.DeviceMacEntity;
import xiaozhi.modules.device.service.DeviceMacService;
import xiaozhi.modules.device.service.DeviceCarModelService;
import xiaozhi.modules.device.entity.DeviceCarModelEntity;

import java.util.Map;
import java.util.HashMap;
import xiaozhi.common.page.PageData;
import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.baomidou.mybatisplus.core.metadata.IPage;
import xiaozhi.common.constant.Constant;

@Service
@AllArgsConstructor
public class DeviceMacServiceImpl extends BaseServiceImpl<DeviceMacDao, DeviceMacEntity> implements DeviceMacService {
    private final DeviceMacDao deviceMacDao;
    private final DeviceCarModelService deviceCarModelService;

    @Override
    public PageData<DeviceMacEntity> queryDeviceMacs(Map<String, Object> params) {
        IPage<DeviceMacEntity> page = getPage(params, "create_date", false);
        
        QueryWrapper<DeviceMacEntity> queryWrapper = new QueryWrapper<>();
        queryWrapper.orderByDesc("create_date");

        if (params.get("deviceNumber") != null && !params.get("deviceNumber").toString().trim().isEmpty()) {
            queryWrapper.like("device_number", params.get("deviceNumber").toString().trim());
        }

        if (params.get("macAddress") != null && !params.get("macAddress").toString().trim().isEmpty()) {
            queryWrapper.like("mac_address", params.get("macAddress").toString().trim());
        }

        if (params.get("deviceName") != null && !params.get("deviceName").toString().trim().isEmpty()) {
            queryWrapper.like("device_name", params.get("deviceName").toString().trim());
        }

        IPage<DeviceMacEntity> resultPage = deviceMacDao.selectPage(page, queryWrapper);
        return new PageData<>(resultPage.getRecords(), resultPage.getTotal());
    }
    
    // 添加:
    @Override
    public String getDeviceConfigByMac(String macAddress) {
        // 根据MAC地址查找设备
        QueryWrapper<DeviceMacEntity> macQueryWrapper = new QueryWrapper<>();
        macQueryWrapper.eq("mac_address", macAddress);
        DeviceMacEntity deviceMac = deviceMacDao.selectOne(macQueryWrapper);
        
        if (deviceMac == null) {
            throw new RuntimeException("未找到该MAC地址对应的设备");
        }
        
        // 根据车型查找指令配置
        QueryWrapper<DeviceCarModelEntity> modelQueryWrapper = new QueryWrapper<>();
        modelQueryWrapper.eq("description", deviceMac.getCarModel());
        DeviceCarModelEntity carModel = deviceCarModelService.selectOne(modelQueryWrapper);
        
        if (carModel == null) {
            throw new RuntimeException("未找到该车型对应的指令配置");
        }
        
        // 构造返回结果
        // Map<String, Object> result = new HashMap<>();
        // result.put("deviceNumber", deviceMac.getDeviceNumber());
        // result.put("macAddress", deviceMac.getMacAddress());
        // result.put("carModel", deviceMac.getCarModel());
        // result.put("deviceName", deviceMac.getDeviceName());
        // result.put("commandConfig", carModel.getCommandConfig());
        
        return carModel.getCommandConfig();
    }
}