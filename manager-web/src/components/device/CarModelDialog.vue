<template>
  <el-dialog :visible="dialogVisible" @update:visible="handleVisibleChange" width="50%" center
    custom-class="custom-dialog" :show-close="false" class="center-dialog">
    <div style="margin: 0 18px; text-align: left; padding: 10px; border-radius: 10px;">
      <div style="font-size: 30px; color: #3d4566; margin-top: -10px; margin-bottom: 10px; text-align: center;">
        {{ editMode ? '编辑车型配置' : '添加车型配置' }}
      </div>

      <button class="custom-close-btn" @click="handleClose">
        ×
      </button>

      <div style="height: 2px; background: #e9e9e9; margin-bottom: 22px;"></div>
      <el-form :model="formData" label-width="100px" label-position="left" class="custom-form">
        <el-form-item label="描述" prop="description">
          <el-input v-model="formData.description" placeholder="请输入描述" class="custom-input-bg"></el-input>
        </el-form-item>
        
        <el-form-item label="指令配置" prop="commandConfig">
          <el-input v-model="formData.commandConfig" placeholder="请输入指令配置" class="custom-input-bg"></el-input>
        </el-form-item>
      </el-form>
    </div>

    <div style="display: flex;justify-content: center;">
      <el-button
        type="primary"
        @click="confirm"
        class="save-btn"
        :loading="saving"
        :disabled="saving">
        保存
      </el-button>
    </div>
  </el-dialog>
</template>

<script>
export default {
  name: 'CarModelDialog',
  props: {
    visible: { type: Boolean, required: true },
    data: { type: Object, default: () => ({}) }
  },
  data() {
    return {
      saving: false,
      dialogVisible: false,
      formData: {
        description: '',
        commandConfig: ''
      }
    }
  },
  computed: {
    editMode() {
      return !!this.data.id;
    }
  },
  watch: {
    visible(val) {
      this.dialogVisible = val;
      if (val) {
        if (this.editMode) {
          this.formData = { ...this.data };
        } else {
          this.resetForm();
        }
      } else {
        this.resetForm();
      }
    }
  },
  methods: {
    handleVisibleChange(val) {
      this.dialogVisible = val;
      this.$emit('update:visible', val);
    },

    handleClose() {
      this.saving = false;
      this.$emit('update:visible', false);
    },

    confirm() {
      this.saving = true;
      try {
        this.$emit('save', { ...this.formData });
        this.$emit('update:visible', false);
      } catch (e) {
        console.error(e);
      } finally {
        this.saving = false;
      }
    },

    resetForm() {
      this.saving = false;
      this.formData = {
        description: '',
        commandConfig: ''
      };
    }
  }
}
</script>

<style scoped>
.custom-dialog {
  position: relative;
  border-radius: 20px;
  overflow: hidden;
  background: white;
  padding-bottom: 17px;
}

.custom-dialog .el-dialog__header {
  padding: 0;
  border-bottom: none;
}

.center-dialog {
  display: flex;
  align-items: center;
  justify-content: center;
}

.center-dialog .el-dialog {
  margin: 0 0 auto !important;
  display: flex;
  flex-direction: column;
}

.custom-close-btn {
  position: absolute;
  top: 20px;
  right: 20px;
  width: 35px;
  height: 35px;
  border-radius: 50%;
  border: 2px solid #cfcfcf;
  background: none;
  font-size: 30px;
  font-weight: lighter;
  color: #cfcfcf;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1;
  padding: 0;
  outline: none;
}

.custom-close-btn:hover {
  color: #409EFF;
  border-color: #409EFF;
}

.custom-form .el-form-item {
  margin-bottom: 20px;
}

.custom-form .el-form-item__label {
  color: #3d4566;
  font-weight: normal;
  text-align: right;
  padding-right: 20px;
}

.custom-input-bg .el-input__inner::-webkit-input-placeholder,
.custom-input-bg .el-textarea__inner::-webkit-input-placeholder {
  color: #9c9f9e;
}

.custom-input-bg .el-input__inner,
.custom-input-bg .el-textarea__inner {
  background-color: #f6f8fc;
}

.save-btn {
  background: #e6f0fd;
  color: #237ff4;
  border: 1px solid #b3d1ff;
  width: 150px;
  height: 40px;
  font-size: 16px;
  transition: all 0.3s ease;
}

.save-btn:hover {
  background: linear-gradient(to right, #237ff4, #9c40d5);
  color: white;
  border: none;
}

[style*="display: flex"] {
  gap: 20px;
}

.custom-input-bg .el-input__inner {
  height: 32px;
}
</style>