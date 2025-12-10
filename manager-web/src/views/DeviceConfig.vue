<template>
  <div class="welcome">
    <HeaderBar />

    <div class="operation-bar">
      <h2 class="page-title">{{ activeTabText }}</h2>
      <div class="action-group">
        <div class="search-group" v-if="activeTab !== 'device-mac' && activeTab !== 'production-batch'">
          <el-input placeholder="请输入关键词查询" v-model="search" class="search-input" clearable
            @keyup.enter.native="handleSearch" style="width: 240px" />
          <el-button class="btn-search" @click="handleSearch">
            搜索
          </el-button>
        </div>
        <!-- 修改: 为设备MAC管理添加具体的三个搜索框 -->
        <div class="search-group" v-else-if="activeTab === 'device-mac'">
          <el-input placeholder="设备号" v-model="searchDeviceNumber" class="search-input" clearable
            @keyup.enter.native="handleSearch" style="width: 150px" />
          <el-input placeholder="MAC地址" v-model="searchMacAddress" class="search-input" clearable
            @keyup.enter.native="handleSearch" style="width: 150px" />
          <el-input placeholder="设备名称" v-model="searchDeviceName" class="search-input" clearable
            @keyup.enter.native="handleSearch" style="width: 150px" />
          <el-button class="btn-search" @click="handleSearch">
            搜索
          </el-button>
        </div>
        <!-- 新增: 为生产批次添加具体搜索框 -->
        <div class="search-group" v-else-if="activeTab === 'production-batch'">
          <el-input placeholder="工厂ID" v-model="searchFactoryId" class="search-input" clearable
            @keyup.enter.native="handleSearch" style="width: 120px" />
          <el-select v-model="searchStatus" placeholder="状态" clearable style="width: 120px">
            <el-option label="待生产" value="0"></el-option>
            <el-option label="生产中" value="1"></el-option>
            <el-option label="已生产" value="2"></el-option>
            <el-option label="已作废" value="9"></el-option>
          </el-select>
          <el-date-picker
            v-model="searchStartDate"
            type="date"
            placeholder="开始日期"
            format="yyyy-MM-dd"
            value-format="yyyy-MM-dd"
            style="width: 140px">
          </el-date-picker>
          <el-input placeholder="硬件版本" v-model="searchHardwareVersion" class="search-input" clearable
            @keyup.enter.native="handleSearch" style="width: 120px" />
          <el-input placeholder="车型ID" v-model="searchModelType" class="search-input" clearable
            @keyup.enter.native="handleSearch" style="width: 120px" />
          <el-button class="btn-search" @click="handleSearch">
            搜索
          </el-button>
        </div>
      </div>
    </div>

    <!-- 主体内容 -->
    <div class="main-wrapper">
      <div class="content-panel">
        <!-- 左侧导航 -->
        <el-menu :default-active="activeTab" class="nav-panel" @select="handleMenuSelect"
          style="background-size: cover; background-position: center;">
          <el-menu-item index="factory">
            <span class="menu-text">工厂管理</span>
          </el-menu-item>
          <el-menu-item index="car-model">
            <span class="menu-text">车型配置</span>
          </el-menu-item>
          <el-menu-item index="production-batch">
            <span class="menu-text">生产批次</span>
          </el-menu-item>
          <el-menu-item index="device-number">
            <span class="menu-text">设备号管理</span>
          </el-menu-item>
          <el-menu-item index="device-mac">
            <span class="menu-text">设备MAC管理</span>
          </el-menu-item>
        </el-menu>

        <!-- 右侧内容 -->
        <div class="content-area">
          <el-card class="model-card" shadow="never">
            <el-table ref="deviceTable" style="width: 100%" v-loading="loading" element-loading-text="拼命加载中"
              element-loading-spinner="el-icon-loading" element-loading-background="rgba(255, 255, 255, 0.7)"
              :header-cell-style="{ background: 'transparent' }" :data="dataList" class="data-table"
              header-row-class-name="table-header" :header-cell-class-name="headerCellClassName"
              @selection-change="handleSelectionChange">
              <el-table-column type="selection" width="55" align="center"></el-table-column>
              
              <!-- 工厂管理列 -->
              <el-table-column v-if="activeTab === 'factory'" label="工厂名称" prop="name" align="center"></el-table-column>
              <el-table-column v-if="activeTab === 'factory'" label="工厂编号" prop="code" align="center"></el-table-column>
              <el-table-column v-if="activeTab === 'factory'" label="国家" prop="country" align="center"></el-table-column>
              <el-table-column v-if="activeTab === 'factory'" label="状态" align="center">
                <template slot-scope="scope">
                  <el-tag :type="scope.row.status === 0 ? 'success' : 'info'">
                    {{ scope.row.status === 0 ? '启用' : '禁用' }}
                  </el-tag>
                </template>
              </el-table-column>
              
              <!-- 车型配置列 -->
              <el-table-column v-if="activeTab === 'car-model'" label="车型ID" prop="id" align="center"></el-table-column>
              <el-table-column v-if="activeTab === 'car-model'" label="描述" prop="description" align="center"></el-table-column>
              <el-table-column v-if="activeTab === 'car-model'" label="指令配置" prop="commandConfig" align="center"></el-table-column>

              
              <!-- 生产批次列 -->
              <el-table-column v-if="activeTab === 'production-batch'" label="工厂ID" prop="factoryId" align="center"></el-table-column>
              <el-table-column v-if="activeTab === 'production-batch'" label="型号" prop="modelType" align="center"></el-table-column>
              <el-table-column v-if="activeTab === 'production-batch'" label="生产日期" prop="productionDate" align="center"></el-table-column>
              <el-table-column v-if="activeTab === 'production-batch'" label="硬件版本" prop="hardwareVersion" align="center"></el-table-column>
              <el-table-column v-if="activeTab === 'production-batch'" label="代理商编码" prop="agentCode" align="center"></el-table-column>
              <!-- 添加开始序号和结束序号列 -->
              <el-table-column v-if="activeTab === 'production-batch'" label="开始序号" prop="startSerialNumber" align="center"></el-table-column>
              <el-table-column v-if="activeTab === 'production-batch'" label="结束序号" prop="endSerialNumber" align="center"></el-table-column>
              <el-table-column v-if="activeTab === 'production-batch'" label="状态" align="center">
                <template slot-scope="scope">
                  <el-tag :type="info">
                    {{ scope.row.status === 0 ? '待生产' : 
                       scope.row.status === 1 ? '生产中' :
                       scope.row.status === 2 ? '已生产' :
                       scope.row.status === 9 ? '已作废' : '其他' }}
                  </el-tag>
                </template>
              </el-table-column>
              
              <!-- 设备号管理列 -->
              <el-table-column v-if="activeTab === 'device-number'" label="批次ID" prop="batchId" align="center"></el-table-column>
              <el-table-column v-if="activeTab === 'device-number'" label="设备号" prop="deviceNumber" align="center"></el-table-column>
              <el-table-column v-if="activeTab === 'device-number'" label="状态" align="center">
                <template slot-scope="scope">
                  <el-tag :type="info">
                    {{ scope.row.status === 1 ? '已生成' : 
                       scope.row.status === 0 ? '已送厂' :
                       scope.row.status === 2 ? '已生产' :
                       scope.row.status === 3 ? '已交付' :
                       scope.row.status === 4 ? '已绑定' : 
                       scope.row.status === 9 ? '已作废' : '其他' }}
                  </el-tag>
                </template>
              </el-table-column>
              
              <!-- 设备MAC管理列 -->
              <el-table-column v-if="activeTab === 'device-mac'" label="设备号" prop="deviceNumber" align="center"></el-table-column>
              <el-table-column v-if="activeTab === 'device-mac'" label="MAC地址" prop="macAddress" align="center"></el-table-column>
              <el-table-column v-if="activeTab === 'device-mac'" label="车型" prop="carModel" align="center"></el-table-column>
              <el-table-column v-if="activeTab === 'device-mac'" label="设备名称" prop="deviceName" align="center"></el-table-column>
              <el-table-column v-if="activeTab === 'device-mac'" label="备注" prop="remark" align="center"></el-table-column>
              <el-table-column v-if="activeTab === 'device-mac'" label="状态" align="center">
                <template slot-scope="scope">
                  <el-tag :type="scope.row.status === 1 ? 'success' : 'info'">
                    {{ scope.row.status === 1 ? '启用' : '禁用' }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column v-if="activeTab === 'device-mac'" label="创建时间" prop="createDate" align="center"></el-table-column>
              
              <el-table-column label="操作" align="center" width="150px">
                <template slot-scope="scope">
                  <el-button type="text" size="mini" @click="editItem(scope.row)" class="edit-btn">
                    修改
                  </el-button>
                  <el-button type="text" size="mini" @click="deleteItem(scope.row)" class="delete-btn">
                    删除
                  </el-button>
                  <!-- 添加创建批次按钮，仅在工厂管理中显示 -->
                  <el-button v-if="activeTab === 'factory'" type="text" size="mini" @click="createBatch(scope.row)" class="batch-btn">
                    创建批次
                  </el-button>
                  <!-- 添加查看批次按钮，仅在工厂管理中显示 -->
                  <el-button v-if="activeTab === 'factory'" type="text" size="mini" @click="viewBatches(scope.row)" class="view-batches-btn">
                    查看批次
                  </el-button>
                  <!-- 添加查看设备号按钮，仅在生产批次中显示 -->
                  <el-button v-if="activeTab === 'production-batch'" type="text" size="mini" @click="viewDeviceNumbers(scope.row)" class="view-devices-btn">
                    查看设备号
                  </el-button>
                </template>
              </el-table-column>
            </el-table>
            <div class="table-footer">
              <div class="batch-actions">
                <el-button size="mini" type="primary" @click="selectAll">
                  {{ isAllSelected ?
                    '取消全选' : '全选' }}
                </el-button>
                <el-button type="success" size="mini" @click="addItem" class="add-btn">
                  新增
                </el-button>
                <el-button size="mini" type="danger" icon="el-icon-delete" @click="batchDelete">
                  删除
                </el-button>
              </div>
              <div class="custom-pagination">

                <el-select v-model="pageSize" @change="handlePageSizeChange" class="page-size-select">
                  <el-option v-for="item in pageSizeOptions" :key="item" :label="`${item}条/页`" :value="item">
                  </el-option>
                </el-select>

                <button class="pagination-btn" :disabled="currentPage === 1" @click="goFirst">首页</button>
                <button class="pagination-btn" :disabled="currentPage === 1" @click="goPrev">上一页</button>

                <button v-for="page in visiblePages" :key="page" class="pagination-btn"
                  :class="{ active: page === currentPage }" @click="goToPage(page)">
                  {{ page }}
                </button>

                <button class="pagination-btn" :disabled="currentPage === pageCount" @click="goNext">下一页</button>
                <span class="total-text">共{{ total }}条记录</span>
              </div>
            </div>
          </el-card>
        </div>
      </div>

      <!-- 对话框组件 -->
      <FactoryDialog :visible.sync="factoryDialogVisible" :data="editData" @save="handleSave" />
      <CarModelDialog :visible.sync="carModelDialogVisible" :data="editData" @save="handleSave" />
      <ProductionBatchDialog :visible.sync="batchDialogVisible" :data="editData" @save="handleSave" />
      <DeviceNumberDialog :visible.sync="deviceNumberDialogVisible" :data="editData" @save="handleSave" />
      <DeviceMacDialog :visible.sync="deviceMacDialogVisible" :data="editData" @save="handleSave" />
      
      <!-- 设备号列表对话框 -->
      <el-dialog title="设备号列表" :visible.sync="devicesDialogVisible" width="60%">
        <div class="device-search-bar" style="margin-bottom: 15px;">
          <el-input
            v-model="deviceSearchKeyword"
            placeholder="请输入设备号进行搜索"
            clearable
            style="width: 300px;"
          ></el-input>
        </div>
        <el-table :data="filteredDeviceNumbersList" v-loading="devicesLoading" height="400" style="width: 100%">
          <el-table-column prop="deviceNumber" label="设备号"></el-table-column>
          <el-table-column prop="status" label="状态" width="150">
            <template slot-scope="scope">
              <el-select 
                v-model="scope.row.status" 
                @change="updateDeviceStatus(scope.row)"
                size="mini"
                style="width: 100px;"
              >
                <el-option label="已生成" :value="0"></el-option>
                <el-option label="已送厂" :value="1"></el-option>
                <el-option label="已生产" :value="2"></el-option>
                <el-option label="已交付" :value="3"></el-option>
                <el-option label="已绑定" :value="4"></el-option>
                <el-option label="已作废" :value="9"></el-option>
              </el-select>
            </template>
          </el-table-column>
        </el-table>
        <span slot="footer" class="dialog-footer">
          <el-button @click="exportDeviceNumbers" type="primary">导出TXT</el-button>
          <el-button @click="devicesDialogVisible = false">关闭</el-button>
        </span>
      </el-dialog>
      
      <!-- 新增: 批次列表对话框 -->
      <el-dialog :title="batchDialogTitle" :visible.sync="batchesDialogVisible" width="70%">
        <el-table :data="batchesList" v-loading="batchesLoading" height="400" style="width: 100%" :default-sort="{prop: 'productionDate', order: 'descending'}">
          <el-table-column prop="factoryId" label="工厂ID" align="center"></el-table-column>
          <el-table-column prop="modelType" label="型号" align="center"></el-table-column>
          <el-table-column prop="productionDate" label="生产日期" align="center" sortable></el-table-column>
          <el-table-column prop="hardwareVersion" label="硬件版本" align="center"></el-table-column>
          <el-table-column prop="agentCode" label="代理商编码" align="center"></el-table-column>
          <el-table-column prop="startSerialNumber" label="开始序号" align="center"></el-table-column>
          <el-table-column prop="endSerialNumber" label="结束序号" align="center"></el-table-column>
          <el-table-column label="状态" align="center">
            <template slot-scope="scope">
              <el-tag :type="info">
                {{ scope.row.status === 0 ? '待生产' : 
                   scope.row.status === 1 ? '生产中' :
                   scope.row.status === 2 ? '已生产' :
                   scope.row.status === 9 ? '已作废' : '其他' }}
              </el-tag>
            </template>
          </el-table-column>
        </el-table>
        <span slot="footer" class="dialog-footer">
          <el-button @click="batchesDialogVisible = false">关闭</el-button>
        </span>
      </el-dialog>
    </div>
    <el-footer>
      <version-footer />
    </el-footer>
  </div>
</template>

<script>
import HeaderBar from "@/components/HeaderBar.vue";
import VersionFooter from "@/components/VersionFooter.vue";
import FactoryDialog from "@/components/device/FactoryDialog.vue";
import CarModelDialog from "@/components/device/CarModelDialog.vue";
import ProductionBatchDialog from "@/components/device/ProductionBatchDialog.vue";
import DeviceNumberDialog from "@/components/device/DeviceNumberDialog.vue";
import DeviceMacDialog from "@/components/device/DeviceMacDialog.vue";
import deviceConfigApi from "@/apis/module/device_config.js";

export default {
  components: { 
    HeaderBar, 
    VersionFooter,
    FactoryDialog,
    CarModelDialog,
    ProductionBatchDialog,
    DeviceNumberDialog,
    DeviceMacDialog
  },
  data() {
    return {
      factoryDialogVisible: false,
      carModelDialogVisible: false,
      batchDialogVisible: false,
      deviceNumberDialogVisible: false,
      deviceMacDialogVisible: false,
      devicesDialogVisible: false, // 新增设备号列表对话框可见性
      batchesDialogVisible: false, // 新增批次列表对话框可见性
      activeTab: 'factory',
      search: '',
      // 添加三个新的搜索字段
      searchDeviceNumber: '',
      searchMacAddress: '',
      searchDeviceName: '',
      // 新增: 生产批次搜索字段
      searchFactoryId: '',
      searchStatus: '',
      searchStartDate: '',
      searchHardwareVersion: '',
      searchModelType: '',
      editData: {},
      dataList: [],
      deviceNumbersList: [], // 存储设备号列表
      batchesList: [], // 存储批次列表
      devicesLoading: false, // 设备号列表加载状态
      batchesLoading: false, // 批次列表加载状态
      pageSizeOptions: [10, 20, 50, 100],
      currentPage: 1,
      pageSize: 10,
      total: 0,
      selectedItems: [],
      isAllSelected: false,
      loading: false,
      deviceSearchKeyword: '', // 添加设备号搜索关键词
      batchDialogTitle: '批次列表', // 添加批次对话框标题
    };
  },

  created() {
    this.loadData();
  },

  computed: {
    activeTabText() {
      const map = {
        'factory': '工厂管理',
        'car-model': '车型配置',
        'production-batch': '生产批次',
        'device-number': '设备号管理',
        'device-mac': '设备MAC管理'
      }
      return map[this.activeTab] || '设备配置'
    },
    pageCount() {
      return Math.ceil(this.total / this.pageSize);
    },
    visiblePages() {
      const pages = [];
      const maxVisible = 3;
      let start = Math.max(1, this.currentPage - 1);
      let end = Math.min(this.pageCount, start + maxVisible - 1);

      if (end - start + 1 < maxVisible) {
        start = Math.max(1, end - maxVisible + 1);
      }

      for (let i = start; i <= end; i++) {
        pages.push(i);
      }
      return pages;
    },
    filteredDeviceNumbersList() {
      if (!this.deviceSearchKeyword) {
        return this.deviceNumbersList;
      }
      return this.deviceNumbersList.filter(item => 
        item.deviceNumber.includes(this.deviceSearchKeyword)
      );
    }
  },

  methods: {
    handlePageSizeChange(val) {
      this.pageSize = val;
      this.currentPage = 1;
      this.loadData();
    },
    headerCellClassName({ column, columnIndex }) {
      if (columnIndex === 0) {
        return 'custom-selection-header';
      }
      return '';
    },
    handleMenuSelect(index) {
      this.activeTab = index;
      this.currentPage = 1;
      this.pageSize = 10;
      // 添加: 切换标签页时清空搜索条件
      if (this.activeTab !== 'device-mac') {
        this.search = '';
      } else {
        this.searchDeviceNumber = '';
        this.searchMacAddress = '';
        this.searchDeviceName = '';
      }
      // 添加: 切换标签页时清空生产批次搜索条件
      if (this.activeTab === 'production-batch') {
        this.searchFactoryId = '';
        this.searchStatus = '';
        this.searchStartDate = '';
        this.searchHardwareVersion = '';
        this.searchModelType = '';
      }
      this.loadData();
    },
    handleSearch() {
      this.currentPage = 1;
      this.loadData();
    },
    // 批量删除
    batchDelete() {
      if (this.selectedItems.length === 0) {
        this.$message.warning('请先选择要删除的项')
        return
      }

      this.$confirm('确定要删除选中的项吗?', '提示', {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }).then(() => {
        // 这里需要根据不同的tab调用不同的删除接口
        this.$message.success('批量删除成功')
        this.loadData()
      }).catch(() => {
        this.$message.info('已取消删除')
      })
    },
    addItem() {
      this.editData = {};
      // 根据当前标签页打开对应的对话框
      this.openDialog(this.activeTab);
    },
    editItem(item) {
      this.editData = JSON.parse(JSON.stringify(item));
      // 根据当前标签页打开对应的对话框
      this.openDialog(this.activeTab);
    },
    // 删除单个项
    deleteItem(item) {
      this.$confirm('确定要删除该项吗?', '提示', {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }).then(() => {
        // 这里需要根据不同的tab调用不同的删除接口
        if (this.activeTab === 'car-model') {
          deviceConfigApi.deleteCarModel(item.id, (response) => {
            if (response.data.code === 0) {
              this.$message.success('删除成功');
              this.loadData();
            } else {
              this.$message.error(response.data.msg || '删除失败');
            }
          });
        } else if (this.activeTab === 'device-mac') {
          deviceConfigApi.deleteDeviceConfig(item.id, (response) => {
            if (response.data.code === 0) {
              this.$message.success('删除成功');
              this.loadData();
            } else {
              this.$message.error(response.data.msg || '删除失败');
            }
          });
        } else {
          this.$message.success('删除成功')
          this.loadData()
        }
      }).catch(() => {
        this.$message.info('已取消删除')
      })
    },
    openDialog(tab_name) {
      // 重置所有对话框状态
      this.factoryDialogVisible = false;
      this.carModelDialogVisible = false;
      this.batchDialogVisible = false;
      this.deviceNumberDialogVisible = false;
      this.deviceMacDialogVisible = false;

      // 根据tab_name, 指定相应的dialog为true
      switch (tab_name) {
        case 'factory':
          this.factoryDialogVisible = true;
          break;
        case 'car-model':
          this.carModelDialogVisible = true;
          break;
        case 'production-batch':
          this.batchDialogVisible = true;
          break;
        case 'device-number':
          this.deviceNumberDialogVisible = true;
          break;
        case 'device-mac':
          this.deviceMacDialogVisible = true;
          break;
        default:
          break;
      }
    },
    // 添加创建批次方法
    createBatch(item) {
      // 初始化生产批次表单数据，将当前工厂ID传入
      this.editData = {
        factoryId: item.id,
        modelType: '',
        productionDate: '',
        hardwareVersion: '',
        agentCode: '',
        status: 0,
        startSerialNumber: null,
        endSerialNumber: null
      };
      // 设置包含工厂名称的标题
      this.batchDialogTitle = `创建批次 - ${item.name}`;
      this.openDialog("production-batch");
    },
    handleCurrentChange(page) {
      this.currentPage = page;
      this.$refs.deviceTable.clearSelection();
    },
    handleSave(data) {
      // 保存逻辑，根据activeTab调用不同的接口
      if (this.activeTab === 'factory') {
        if (data.factoryId) { // 创建批次 
           deviceConfigApi.createProductionBatch(data, (response) => {
            if (response.data.code === 0) {
              this.$message.success('创建成功');
              // 关闭对应对话框
              this.openDialog('');
              this.loadData();
            } else {
              this.$message.error(response.data.msg || '创建失败');
            }
          });
        } else if (data.id) {
          deviceConfigApi.updateFactory(data.id, data, (response) => {
            if (response.data.code === 0) {
              this.$message.success('更新成功');
              // 关闭对应对话框
              this.openDialog('');
              this.loadData();
            } else {
              this.$message.error(response.data.msg || '更新失败');
            }
          });
        } else {
          deviceConfigApi.createFactory(data, (response) => {
            if (response.data.code === 0) {
              this.$message.success('创建成功');
              // 关闭对应对话框
              this.openDialog('');
              this.loadData();
            } else {
              this.$message.error(response.data.msg || '创建失败');
            }
          });
        }
      } else if (this.activeTab === 'car-model') {
        if (data.id) {
          deviceConfigApi.updateCarModel(data.id, data, (response) => {
            if (response.data.code === 0) {
              this.$message.success('更新成功');
              // 关闭对应对话框
              this.openDialog('');
              this.loadData();
            } else {
              this.$message.error(response.data.msg || '更新失败');
            }
          });
        } else {
          deviceConfigApi.createCarModel(data, (response) => {
            if (response.data.code === 0) {
              this.$message.success('创建成功');
              // 关闭对应对话框
              this.openDialog('');
              this.loadData();
            } else {
              this.$message.error(response.data.msg || '创建失败');
            }
          });
        }
      } else if (this.activeTab === 'production-batch') {
        if (data.id) {
          // 更新生产批次
          this.$message.success('更新成功');
          // 关闭对应对话框
          this.openDialog('');
          this.loadData();

          //todo update 

        } else {
          deviceConfigApi.createProductionBatch(data, (response) => {
            if (response.data.code === 0) {
              this.$message.success('创建成功');
              // 关闭对应对话框
              this.openDialog('');
              this.loadData();
            } else {
              this.$message.error(response.data.msg || '创建失败');
            }
          });
        }
      } else if (this.activeTab === 'device-number') {
        // 设备号管理保存逻辑
        this.$message.success('保存成功');
        // 关闭对应对话框
        this.openDialog('');
        this.loadData();
      } else if (this.activeTab === 'device-mac') {
        // 设备MAC管理保存逻辑
        if (data.id) {
          deviceConfigApi.updateDeviceConfig(data.id, data, (response) => {
            if (response.data.code === 0) {
              this.$message.success('更新成功');
              this.openDialog('');
              this.loadData();
            } else {
              this.$message.error(response.data.msg || '更新失败');
            }
          });
        } else {
          deviceConfigApi.createDeviceConfig(data, (response) => {
            if (response.data.code === 0) {
              this.$message.success('创建成功');
              this.openDialog('');
              this.loadData();
            } else {
              this.$message.error(response.data.msg || '创建失败');
            }
          });
        }
      }
    },
    selectAll() {
      if (this.isAllSelected) {
        this.$refs.deviceTable.clearSelection();
      } else {
        this.$refs.deviceTable.toggleAllSelection();
      }
    },
    handleSelectionChange(val) {
      this.selectedItems = val;
      this.isAllSelected = val.length === this.dataList.length;
      if (val.length === 0) {
        this.isAllSelected = false;
      }
    },

    // 分页器
    goFirst() {
      this.currentPage = 1;
      this.loadData();
    },
    goPrev() {
      if (this.currentPage > 1) {
        this.currentPage--;
        this.loadData();
      }
    },
    goNext() {
      if (this.currentPage < this.pageCount) {
        this.currentPage++;
        this.loadData();
      }
    },
    goToPage(page) {
      this.currentPage = page;
      this.loadData();
    },

    // 获取数据列表
    loadData() {
      this.loading = true;
      if (this.activeTab === 'factory') {
        // 调用后端接口获取工厂数据
        const params = {
          page: this.currentPage,
          limit: this.pageSize,
          name: this.search // 搜索工厂名称
        };
        
        deviceConfigApi.getFactories(params, (response) => {
          if (response.data.code === 0) {
            this.dataList = response.data.data.list;
            this.total = response.data.data.total;
          } else {
            this.$message.error(response.data.msg || '获取工厂数据失败');
          }
          this.loading = false;
        });
      } else if (this.activeTab === 'car-model') {
        const params = { 
          page: this.currentPage,
          limit: this.pageSize,
          name: this.search // 汽车模型名称
        };
        
        deviceConfigApi.getCarModels(params, (response) => {
          if (response.data.code === 0) {
            this.dataList = response.data.data.list;
            this.total = response.data.data.total;
          } else {
            this.$message.error(response.data.msg || '获取车型配置数据失败');
          }
          this.loading = false;
        });
      } else if (this.activeTab === 'production-batch') {
        // 修改: 添加所有生产批次搜索条件
        const params = {
          page: this.currentPage,
          limit: this.pageSize,
          factoryId: this.searchFactoryId,
          status: this.searchStatus,
          productionDate: this.searchStartDate,
          hardwareVersion: this.searchHardwareVersion,
          modelType: this.searchModelType
        };
        
        deviceConfigApi.getProductionBatches(params, (response) => {
          if (response.data.code === 0) {
            this.dataList = response.data.data.list;
            this.total = response.data.data.total;
          } else {
            this.$message.error(response.data.msg || '获取生产批次数据失败');
          }
          this.loading = false;
        });
      } else if (this.activeTab === 'device-number') {
        // 添加设备号管理的真实数据调用
        const params = {
          page: this.currentPage,
          limit: this.pageSize,
          name: this.search // 设备号模糊搜素
        };
        
        deviceConfigApi.getDeviceNumbers(params, (response) => {
          if (response.data.code === 0) {
            this.dataList = response.data.data.list;
            this.total = response.data.data.total;
          } else {
            this.$message.error(response.data.msg || '获取设备号数据失败');
          }
          this.loading = false;
        });
      } else if (this.activeTab === 'device-mac') {
        // 修改: 使用三个具体字段进行搜索
        const params = {
          page: this.currentPage,
          limit: this.pageSize,
          deviceNumber: this.searchDeviceNumber.trim(),
          macAddress: this.searchMacAddress.trim(),
          deviceName: this.searchDeviceName.trim()
        };
        
        deviceConfigApi.getDeviceConfigs(params, (response) => {
          if (response.data.code === 0) {
            this.dataList = response.data.data.list;
            this.total = response.data.data.total;
          } else {
            this.$message.error(response.data.msg || '获取设备MAC数据失败');
          }
          this.loading = false;
        });
      } else {
        // 其他tab的模拟数据保持不变
        setTimeout(() => {
          this.dataList = [];
          for (let i = 0; i < this.pageSize; i++) {
            const index = (this.currentPage - 1) * this.pageSize + i;
            if (this.activeTab === 'device-config') {
              this.dataList.push({
                id: index + 1,
                name: `配置项${index + 1}`,
                value: `값{index + 1}`
              });
            }
          }
          this.total = 100;
          this.loading = false;
        }, 500);
      }
    },
    
    // 添加更新设备状态的方法
    updateDeviceStatus(row) {
      deviceConfigApi.updateDeviceNumberStatus(row.id, row.status, (response) => {
        if (response.data.code === 0) {
          this.$message.success('状态更新成功');
          // 更新本地列表中的状态
          const index = this.deviceNumbersList.findIndex(item => item.id === row.id);
          if (index !== -1) {
            this.deviceNumbersList.splice(index, 1, {...row});
          }
        } else {
          this.$message.error(response.data.msg || '状态更新失败');
          // 如果更新失败，恢复原状态
          const originalItem = this.deviceNumbersList.find(item => item.id === row.id);
          if (originalItem) {
            originalItem.status = row.originalStatus;
          }
        }
      });
    },
    
    // 查看设备号方法
    viewDeviceNumbers(row) {
      this.devicesLoading = true;
      this.devicesDialogVisible = true;
      this.deviceNumbersList = [];
      this.deviceSearchKeyword = ''; // 清空搜索关键词
      
      const params = {
        page: 1,
        limit: 1000 // 获取所有设备号
      };
      
      deviceConfigApi.getDeviceNumbersByBatch(row.id, params, (response) => {
        if (response.data.code === 0) {
          console.log("resp data list: ", response.data.data.list)
          this.deviceNumbersList = response.data.data.list || [];
          console.log("deviceNumbersList len333", this.deviceNumbersList.length);

          // 保存原始状态以便在更新失败时恢复
          this.deviceNumbersList.forEach(item => {
            item.originalStatus = item.status;
          });
        } else {
          this.$message.error(response.data.msg || '获取设备号列表失败');
        }
        this.devicesLoading = false;
      });

      console.log("deviceNumbersList444", this.deviceNumbersList.length);
    },
    
    // 关闭设备号对话框
    handleDevicesDialogClose(done) {
      /*
      this.$confirm('确认关闭？')
        .then(_ => {
          done();
        })
        .catch(_ => {});
      */
    },
    
    // 关闭批次对话框
    handleBatchesDialogClose(done) {
      /*
      this.$confirm('确认关闭？')
        .then(_ => {
          done();
        })
        .catch(_ => {});
      */
    },
    
    // 查看批次方法
    viewBatches(row) {
      this.batchesLoading = true;
      this.batchesDialogVisible = true;
      this.batchesList = [];
      
      // 设置包含工厂名称的标题
      this.batchDialogTitle = `批次列表 - ${row.name}`;
      
      const params = {
        factoryId: row.id,
        page: 1,
        limit: 10000 // 设置一个较大的数值以获取所有数据
      };
      
      deviceConfigApi.getProductionBatches(params, (response) => {
        if (response.data.code === 0) {
          this.batchesList = response.data.data.list || [];
        } else {
          this.$message.error(response.data.msg || '获取批次列表失败');
        }
        this.batchesLoading = false;
      });
    },
    
    // 导出设备号到TXT文件
    exportDeviceNumbers() {
      if (!this.deviceNumbersList || this.deviceNumbersList.length === 0) {
        this.$message.warning('没有设备号可以导出');
        return;
      }
      
      const content = this.deviceNumbersList.map(item => item.deviceNumber).join('\n');
      const blob = new Blob([content], { type: 'text/plain;charset=utf-8' });
      const link = document.createElement('a');
      link.href = URL.createObjectURL(blob);
      link.download = 'device_numbers.txt';
      link.click();
      URL.revokeObjectURL(link.href);
      this.$message.success('导出成功');
    },
  },
};
</script>


<style scoped>
.el-switch {
  height: 23px;
}

::v-deep .el-table tr {
  background: transparent;
}

.welcome {
  min-width: 900px;
  min-height: 506px;
  height: 100vh;
  display: flex;
  position: relative;
  flex-direction: column;
  background-size: cover;
  background: linear-gradient(to bottom right, #dce8ff, #e4eeff, #e6cbfd) center;
  -webkit-background-size: cover;
  -o-background-size: cover;
}

.main-wrapper {
  margin: 5px 22px;
  border-radius: 15px;
  min-height: calc(100vh - 26vh);
  height: auto;
  max-height: 80vh;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
  position: relative;
  background: rgba(237, 242, 255, 0.5);
}

.operation-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 24px;
}

.page-title {
  font-size: 24px;
  margin: 0;
}

.content-panel {
  flex: 1;
  display: flex;
  overflow: hidden;
  height: 100%;
  border-radius: 15px;
  background: transparent;
  border: 1px solid #fff;
}

.nav-panel {
  min-width: 242px;
  height: 100%;
  border-right: 1px solid #ebeef5;
  background:
    linear-gradient(120deg,
      rgba(107, 140, 255, 0.3) 0%,
      rgba(169, 102, 255, 0.3) 25%,
      transparent 60%),
    url("../assets/model/model.png") no-repeat center / cover;
  padding: 16px 0;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
}

.nav-panel .el-menu-item {
  height: 50px;
  background: #e9f0ff;
  line-height: 50px;
  border-radius: 4px 0 0 4px !important;
  transition: all 0.3s;
  display: flex !important;
  justify-content: flex-end;
  padding-right: 12px !important;
  width: fit-content;
  margin: 8px 0 8px auto;
  min-width: unset;
}

.nav-panel .el-menu-item.is-active {
  background: #5778ff;
  position: relative;
  padding-left: 40px !important;
}

.nav-panel .el-menu-item.is-active::before {
  content: '';
  position: absolute;
  left: 15px;
  top: 50%;
  transform: translateY(-50%);
  width: 13px;
  height: 13px;
  background: #fff;
  border-radius: 50%;
  box-shadow: 0 0 4px rgba(64, 158, 255, 0.5);
}

.menu-text {
  font-size: 14px;
  color: #606266;
  text-align: right;
  width: 100%;
  padding-right: 8px;
}

.content-area {
  flex: 1;
  padding: 24px;
  height: 100%;
  min-width: 600px;
  overflow: hidden;
  background-color: white;
  display: flex;
  flex-direction: column;
}

.action-group {
  display: flex;
  align-items: center;
  gap: 16px;
}

.search-group {
  display: flex;
  gap: 10px;
}

.search-input {
  width: 240px;
}

.btn-search {
  background: linear-gradient(135deg, #6b8cff, #a966ff);
  border: none;
  color: white;
}

.btn-search:hover {
  opacity: 0.9;
  transform: translateY(-1px);
}

::v-deep .search-input .el-input__inner {
  border-radius: 4px;
  border: 1px solid #DCDFE6;
  background-color: white;
  transition: border-color 0.2s;
}

::v-deep .page-size-select {
  width: 100px;
  margin-right: 8px;
}

::v-deep .page-size-select .el-input__inner {
  height: 32px;
  line-height: 32px;
  border-radius: 4px;
  border: 1px solid #e4e7ed;
  background: #dee7ff;
  color: #606266;
  font-size: 14px;
}

::v-deep .page-size-select .el-input__suffix {
  right: 6px;
  width: 15px;
  height: 20px;
  display: flex;
  justify-content: center;
  align-items: center;
  top: 6px;
  border-radius: 4px;
}

::v-deep .page-size-select .el-input__suffix-inner {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
}

::v-deep .page-size-select .el-icon-arrow-up:before {
  content: "";
  display: inline-block;
  border-left: 6px solid transparent;
  border-right: 6px solid transparent;
  border-top: 9px solid #606266;
  position: relative;
  transform: rotate(0deg);
  transition: transform 0.3s;
}

::v-deep .search-input .el-input__inner:focus {
  border-color: #6b8cff;
  outline: none;
}

.data-table {
  border-radius: 6px;
  overflow: hidden;
  background-color: transparent !important;
}

.data-table /deep/ .el-table__row {
  background-color: transparent !important;
}

.table-header th {
  background-color: transparent !important;
  color: #606266;
  font-weight: 600;
}

.table-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 0;
  width: 100%;
  flex-shrink: 0;
  min-height: 60px;
  background: white;
}

.batch-actions {
  display: flex;
  gap: 8px;
}

.batch-actions .el-button {
  min-width: 72px;
  height: 32px;
  padding: 7px 12px 7px 10px;
  font-size: 12px;
  border-radius: 4px;
  line-height: 1;
  font-weight: 500;
  border: none;
  transition: all 0.3s ease;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.1);
}

.batch-actions .el-button:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.15);
}

.batch-actions .el-button--primary {
  background: #5f70f3 !important;
  color: white;
}

.batch-actions .el-button--success {
  background: #5bc98c;
  color: white;
}

.batch-actions .el-button--danger {
  background: #fd5b63;
  color: white;
}

.batch-actions .el-button:first-child {
  background: linear-gradient(135deg, #409EFF, #6B8CFF);
  border: none;
  color: white;
}

.batch-actions .el-button:first-child:hover {
  background: linear-gradient(135deg, #3A8EE6, #5A7CFF);
}

.el-table th /deep/ .el-table__cell {
  overflow: hidden;
  -webkit-user-select: none;
  -moz-user-select: none;
  user-select: none;
  background-color: transparent !important;
}

::v-deep .el-table .custom-selection-header .cell .el-checkbox__inner {
  display: none !important;
}

::v-deep .el-table .custom-selection-header .cell::before {
  content: '选择';
  display: block;
  text-align: center;
  line-height: 0;
  color: black;
  margin-top: 23px;
}

::v-deep .el-table__body .el-checkbox__inner {
  display: inline-block !important;
  background: #e6edfa;
}

::v-deep .el-table thead th:not(:first-child) .cell {
  color: #303133 !important;
}

::v-deep .nav-panel .el-menu-item.is-active .menu-text {
  color: #fff !important;
}

::v-deep .data-table {

  &.el-table::before,
  &.el-table::after,
  &.el-table__inner-wrapper::before {
    display: none !important;
  }
}

::v-deep .data-table .el-table__header-wrapper {
  border-bottom: 1px solid rgb(224, 227, 237);
}

::v-deep .data-table .el-table__body td {
  border-bottom: 1px solid rgb(224, 227, 237) !important;
}

.el-button img {
  height: 1em;
  vertical-align: middle;
  padding-right: 2px;
  padding-bottom: 2px;
}

::v-deep .el-checkbox__inner {
  border-color: #cfcfcf !important;
  transition: all 0.2s ease-in-out;
}

::v-deep .el-checkbox__input.is-checked .el-checkbox__inner {
  background-color: #5f70f3;
  border-color: #5f70f3;
}

.voice-management-btn {
  background: #9db3ea;
  color: white;
  min-width: 68px;
  line-height: 14px;
  white-space: nowrap;
  transition: all 0.3s;
  border-radius: 10px;
}

.voice-management-btn:hover {
  background: #8aa2e0;
  /* 悬停时颜色加深 */
  transform: scale(1.05);
}

::v-deep .el-table .el-table-column--selection .cell {
  padding-left: 15px !important;
}

::v-deep .el-table .el-table__fixed-right .cell {
  padding-right: 15px !important;
}

.edit-btn,
.delete-btn {
  margin: 0 8px;
  color: #7079aa !important;
}

::v-deep .el-table .cell {
  padding-left: 10px;
  padding-right: 10px;
}

/* 分页器 */
.custom-pagination {
  display: flex;
  align-items: center;
  gap: 8px;

  /* 导航按钮样式 (首页、上一页、下一页) */
  .pagination-btn:first-child,
  .pagination-btn:nth-child(2),
  .pagination-btn:nth-child(3),
  .pagination-btn:nth-last-child(2) {
    min-width: 60px;
    height: 32px;
    padding: 0 12px;
    border-radius: 4px;
    border: 1px solid #e4e7ed;
    background: #DEE7FF;
    color: #606266;
    font-size: 14px;
    cursor: pointer;
    transition: all 0.3s ease;

    &:hover {
      background: #d7dce6;
    }

    &:disabled {
      opacity: 0.6;
      cursor: not-allowed;
    }
  }

  /* 数字按钮样式 */
  .pagination-btn:not(:first-child):not(:nth-child(2)):not(:nth-child(3)):not(:nth-last-child(2)) {
    min-width: 28px;
    height: 32px;
    padding: 0;
    border-radius: 4px;
    border: 1px solid transparent;
    background: transparent;
    color: #606266;
    font-size: 14px;
    cursor: pointer;
    transition: all 0.3s ease;

    &:hover {
      background: rgba(245, 247, 250, 0.3);
    }
  }

  .pagination-btn.active {
    background: #5f70f3 !important;
    color: #ffffff !important;
    border-color: #5f70f3 !important;

    &:hover {
      background: #6d7cf5 !important;
    }
  }

  .total-text {
    color: #909399;
    font-size: 14px;
    margin-left: 10px;
  }
}

.model-card {
  background: white;
  flex: 1;
  display: flex;
  flex-direction: column;
  border: none;
  box-shadow: none;
  overflow: hidden;
}

.model-card ::v-deep .el-card__body {
  padding: 0;
  display: flex;
  flex-direction: column;
  flex: 1;
  overflow: hidden;
}

.data-table {
  --table-max-height: calc(100vh - 45vh);
  max-height: var(--table-max-height);
}

.data-table ::v-deep .el-table__body-wrapper {
  max-height: calc(var(--table-max-height) - 80px);
  overflow-y: auto;
}

::v-deep .el-loading-mask {
  background-color: rgba(255, 255, 255, 0.6) !important;
  backdrop-filter: blur(2px);
}

::v-deep .el-loading-spinner .circular {
  width: 28px;
  height: 28px;
}

::v-deep .el-loading-spinner .path {
  stroke: #6b8cff;
}

::v-deep .el-loading-text {
  color: #6b8cff !important;
  font-size: 14px;
  margin-top: 8px;
}
</style>
