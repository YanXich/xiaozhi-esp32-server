package xiaozhi.modules.device.service.impl;

import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.baomidou.mybatisplus.core.metadata.IPage;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import xiaozhi.modules.device.dao.DeviceProductionBatchDao;
import xiaozhi.modules.device.entity.DeviceProductionBatchEntity;
import xiaozhi.modules.device.dto.DeviceProductionBatchDTO;

import java.util.Arrays;
import java.util.List;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
class DeviceProductionBatchServiceImplTest {

    @Mock
 private DeviceProductionBatchDao deviceProductionBatchDao;

    @InjectMocks
    private DeviceProductionBatchServiceImpl deviceProductionBatchService;

    @Test
    void queryBatches_WithValidQuery_ReturnsPageData() {
        // Given
        DeviceProductionBatchDTO queryDTO = new DeviceProductionBatchDTO();
        queryDTO.setPage(1);
        queryDTO.setLimit(10);
        queryDTO.setFactoryId(1L);
        queryDTO.setModelType("model1");
        queryDTO.setStatus("0");
        queryDTO.setStartDate("2023-01-01");
        queryDTO.setEndDate("2023-12-31");

        DeviceProductionBatchEntity batch1 = new DeviceProductionBatchEntity();
        batch1.setId("batch1");
        batch1.setFactoryId(1L);
        batch1.setModelType("model1");
        batch1.setStatus(0); // Using Integer instead of enum

        IPage<DeviceProductionBatchEntity> page = new Page<>();
        page.setRecords(Arrays.asList(batch1));
        page.setTotal(1L);

        when(deviceProductionBatchDao.selectPage(any(), any())).thenReturn(page);

        // When
        var result = deviceProductionBatchService.queryBatches(queryDTO);

        // Then
        assertNotNull(result);
        assertEquals(1, result.getTotal());
        assertEquals(1, result.getList().size());
        verify(deviceProductionBatchDao, times(1)).selectPage(any(), any());
    }

    @Test
    void listBatches_WithValidQuery_ReturnsList() {
        // Given
        DeviceProductionBatchDTO queryDTO = new DeviceProductionBatchDTO();
        queryDTO.setFactoryId(1L);
        queryDTO.setModelType("model1");
        queryDTO.setStatus("0");

        DeviceProductionBatchEntity batch1 = new DeviceProductionBatchEntity();
        batch1.setId("batch1");
        batch1.setFactoryId(1L);
        batch1.setModelType("model1");
        batch1.setStatus(0); // Using Integer instead of enum

        when(deviceProductionBatchDao.selectList(any(QueryWrapper.class))).thenReturn(Arrays.asList(batch1));

        // When
        List<DeviceProductionBatchEntity> result = deviceProductionBatchService.listBatches(queryDTO);

        // Then
        assertNotNull(result);
        assertEquals(1, result.size());
        assertEquals("batch1", result.get(0).getId());
        verify(deviceProductionBatchDao, times(1)).selectList(any(QueryWrapper.class));
    }
}