package xiaozhi.modules.device.dao;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import org.apache.ibatis.annotations.Mapper;
import xiaozhi.modules.device.entity.DeviceFactoryEntity;

@Mapper
public interface DeviceFactoryDao extends BaseMapper<DeviceFactoryEntity> {
}