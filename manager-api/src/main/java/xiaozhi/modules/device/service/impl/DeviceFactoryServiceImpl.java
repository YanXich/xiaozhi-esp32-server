package xiaozhi.modules.device.service.impl;

import lombok.AllArgsConstructor;
import org.springframework.stereotype.Service;
import xiaozhi.common.service.impl.BaseServiceImpl;
import xiaozhi.modules.device.dao.DeviceFactoryDao;
import xiaozhi.modules.device.entity.DeviceFactoryEntity;
import xiaozhi.modules.device.service.DeviceFactoryService;
import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.baomidou.mybatisplus.core.metadata.IPage;
import xiaozhi.common.page.PageData;
import xiaozhi.modules.device.dto.DeviceFactoryQueryDTO;
import java.util.List;
import java.util.HashMap;
import java.util.Map;
import xiaozhi.common.constant.Constant;

@Service
@AllArgsConstructor
public class DeviceFactoryServiceImpl extends BaseServiceImpl<DeviceFactoryDao, DeviceFactoryEntity> implements DeviceFactoryService {
    
    private final DeviceFactoryDao deviceFactoryDao;
    
    @Override
    public PageData<DeviceFactoryEntity> queryFactories(DeviceFactoryQueryDTO queryDTO) {
        // 修复分页参数传递问题，确保类型正确
        Map<String, Object> params = new HashMap<>();
        params.put(Constant.PAGE, String.valueOf(queryDTO.getPage()));
        params.put(Constant.LIMIT, String.valueOf(queryDTO.getLimit()));
        IPage<DeviceFactoryEntity> page = getPage(params, "create_date", false);
        
        QueryWrapper<DeviceFactoryEntity> queryWrapper = buildQueryWrapper(queryDTO);
        
        IPage<DeviceFactoryEntity> resultPage = deviceFactoryDao.selectPage(page, queryWrapper);
        return new PageData<>(resultPage.getRecords(), resultPage.getTotal());
    }
    
    @Override
    public List<DeviceFactoryEntity> listFactories(DeviceFactoryQueryDTO queryDTO) {
        QueryWrapper<DeviceFactoryEntity> queryWrapper = buildQueryWrapper(queryDTO);
        return deviceFactoryDao.selectList(queryWrapper);
    }
    
    private QueryWrapper<DeviceFactoryEntity> buildQueryWrapper(DeviceFactoryQueryDTO queryDTO) {
        QueryWrapper<DeviceFactoryEntity> queryWrapper = new QueryWrapper<>();
        
        // 名称模糊查询
        if (queryDTO.getName() != null && !queryDTO.getName().trim().isEmpty()) {
            queryWrapper.like("name", queryDTO.getName().trim());
        }
        
        // 编号精确查询
        if (queryDTO.getCode() != null && !queryDTO.getCode().trim().isEmpty()) {
            queryWrapper.eq("code", queryDTO.getCode().trim());
        }
        
        // 状态查询 (现在使用数字而不是枚举)
        if (queryDTO.getStatus() != null && !queryDTO.getStatus().trim().isEmpty()) {
            queryWrapper.eq("status", Integer.parseInt(queryDTO.getStatus()));
        }
        
        // 修改排序字段为create_date
        queryWrapper.orderByDesc("create_date");
        return queryWrapper;
    }
}