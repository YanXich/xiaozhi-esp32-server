package xiaozhi.modules.device.service.impl;

import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.baomidou.mybatisplus.core.metadata.IPage;
import lombok.AllArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import xiaozhi.common.page.PageData;
import xiaozhi.common.service.impl.BaseServiceImpl;
import xiaozhi.modules.device.dao.DeviceCarModelDao;
import xiaozhi.modules.device.dto.DeviceCarModelDTO;
import xiaozhi.modules.device.entity.DeviceCarModelEntity;
import xiaozhi.modules.device.service.DeviceCarModelService;

import java.util.List;
import java.util.Map;

@Slf4j
@Service
@AllArgsConstructor
public class DeviceCarModelServiceImpl extends BaseServiceImpl<DeviceCarModelDao, DeviceCarModelEntity> implements DeviceCarModelService {

    private final DeviceCarModelDao deviceCarModelDao;

    @Override
    public PageData<DeviceCarModelEntity> queryCarModels(Map<String, Object> params) {
        IPage<DeviceCarModelEntity> page = getPage(params, "create_date", false);

        QueryWrapper<DeviceCarModelEntity> queryWrapper = new QueryWrapper<>();
        queryWrapper.orderByDesc("create_date");

        // 检查params中是否有name参数，如果不为空字符串，则模糊搜索description字段
        if (params.get("name") != null && !params.get("name").toString().trim().isEmpty()) {
            queryWrapper.like("description", params.get("name").toString().trim());
        }

        IPage<DeviceCarModelEntity> resultPage = deviceCarModelDao.selectPage(page, queryWrapper);
        return new PageData<>(resultPage.getRecords(), resultPage.getTotal());
    }

    @Override
    public List<DeviceCarModelEntity> listCarModels(DeviceCarModelDTO queryDTO) {
        QueryWrapper<DeviceCarModelEntity> queryWrapper = new QueryWrapper<>();
        queryWrapper.orderByDesc("create_date");
        return deviceCarModelDao.selectList(queryWrapper);
    }

    @Override
    public void delete(Long id) {
        deviceCarModelDao.deleteById(id);
    }

    // 添加selectOne方法实现
    @Override
    public DeviceCarModelEntity selectOne(QueryWrapper<DeviceCarModelEntity> queryWrapper) {
        return deviceCarModelDao.selectOne(queryWrapper);
    }
}