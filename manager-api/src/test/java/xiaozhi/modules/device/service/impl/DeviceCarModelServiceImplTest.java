package xiaozhi.modules.device.service.impl;

import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.baomidou.mybatisplus.core.metadata.IPage;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import xiaozhi.modules.device.dao.DeviceCarModelDao;
import xiaozhi.modules.device.entity.DeviceCarModelEntity;
import xiaozhi.modules.device.dto.DeviceCarModelDTO;

import java.util.Arrays;
import java.util.List;
import java.util.HashMap;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
class DeviceCarModelServiceImplTest {

    @Mock
    private DeviceCarModelDao deviceCarModelDao;

    @InjectMocks
    private DeviceCarModelServiceImpl deviceCarModelService;

    @Test
    void queryCarModels_WithValidParams_ReturnsPageData() {
        // Given
        Map<String, Object> params = new HashMap<>();
        params.put("page", "1");
        params.put("limit", "10");

        DeviceCarModelEntity model1 = new DeviceCarModelEntity();
        model1.setId("model1");
        model1.setDescription("BMW X5");
        model1.setCommandConfig("{\"command\": \"test\"}");

        IPage<DeviceCarModelEntity> page = new Page<>();
        page.setRecords(Arrays.asList(model1));
        page.setTotal(1L);

        when(deviceCarModelDao.selectPage(any(), any())).thenReturn(page);

        // When
        var result = deviceCarModelService.queryCarModels(params);

        // Then
        assertNotNull(result);
        assertEquals(1, result.getTotal());
        assertEquals(1, result.getList().size());
        verify(deviceCarModelDao, times(1)).selectPage(any(), any());
    }

    @Test
    void listCarModels_ReturnsList() {
        // Given
        DeviceCarModelDTO queryDTO = new DeviceCarModelDTO();

        DeviceCarModelEntity model1 = new DeviceCarModelEntity();
        model1.setId("model1");
        model1.setDescription("BMW X5");
        model1.setCommandConfig("{\"command\": \"test\"}");

        when(deviceCarModelDao.selectList(any(QueryWrapper.class))).thenReturn(Arrays.asList(model1));

        // When
        List<DeviceCarModelEntity> result = deviceCarModelService.listCarModels(queryDTO);

        // Then
        assertNotNull(result);
        assertEquals(1, result.size());
        assertEquals("BMW X5", result.get(0).getDescription());
        verify(deviceCarModelDao, times(1)).selectList(any(QueryWrapper.class));
    }
}