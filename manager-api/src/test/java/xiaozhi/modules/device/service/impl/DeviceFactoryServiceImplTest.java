package xiaozhi.modules.device.service.impl;

import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.baomidou.mybatisplus.core.metadata.IPage;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import xiaozhi.modules.device.dao.DeviceFactoryDao;
import xiaozhi.modules.device.entity.DeviceFactoryEntity;
import xiaozhi.modules.device.dto.DeviceFactoryQueryDTO;

import java.util.Arrays;
import java.util.List;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
class DeviceFactoryServiceImplTest {

    @Mock
    private DeviceFactoryDao deviceFactoryDao;

    @InjectMocks
    private DeviceFactoryServiceImpl deviceFactoryService;

    @Test
    void queryFactories_WithValidQuery_ReturnsPageData() {
        // Given
        DeviceFactoryQueryDTO queryDTO = new DeviceFactoryQueryDTO();
        queryDTO.setPage(1);
        queryDTO.setLimit(10);
        queryDTO.setName("test");
        queryDTO.setCode("001");
        queryDTO.setStatus("0");

        DeviceFactoryEntity factory1 = new DeviceFactoryEntity();
        factory1.setId(1L);
        factory1.setName("test factory");
        factory1.setCode("001");
        factory1.setStatus(0); // Using Integer instead of enum

        IPage<DeviceFactoryEntity> page = new Page<>();
        page.setRecords(Arrays.asList(factory1));
        page.setTotal(1L);

        when(deviceFactoryDao.selectPage(any(), any())).thenReturn(page);

        // When
        var result = deviceFactoryService.queryFactories(queryDTO);

        // Then
        assertNotNull(result);
        assertEquals(1, result.getTotal());
        assertEquals(1, result.getList().size());
        verify(deviceFactoryDao, times(1)).selectPage(any(), any());
    }

    @Test
    void listFactories_WithValidQuery_ReturnsList() {
        // Given
        DeviceFactoryQueryDTO queryDTO = new DeviceFactoryQueryDTO();
        queryDTO.setName("test");
        queryDTO.setCode("001");
        queryDTO.setStatus("0");

        DeviceFactoryEntity factory1 = new DeviceFactoryEntity();
        factory1.setId(1L);
        factory1.setName("test factory");
        factory1.setCode("001");
        factory1.setStatus(0); // Using Integer instead of enum

        when(deviceFactoryDao.selectList(any(QueryWrapper.class))).thenReturn(Arrays.asList(factory1));

        // When
        List<DeviceFactoryEntity> result = deviceFactoryService.listFactories(queryDTO);

        // Then
        assertNotNull(result);
        assertEquals(1, result.size());
        assertEquals("test factory", result.get(0).getName());
        verify(deviceFactoryDao, times(1)).selectList(any(QueryWrapper.class));
    }
}