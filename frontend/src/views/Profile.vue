<template>
  <div class="profile-page">
    <el-page-header @back="goBack" title="返回">
      <template #content>
        <span class="page-header-title">个人资料</span>
      </template>
    </el-page-header>

    <el-card class="main-card">
      <template #header>头像</template>
      <div class="avatar-row">
        <el-avatar :size="96" :src="avatarDisplayUrl">
          {{ userInitial }}
        </el-avatar>
        <el-upload
          ref="avatarUploadRef"
          class="avatar-uploader"
          :auto-upload="false"
          :show-file-list="false"
          accept="image/jpeg,image/jpg,image/png,image/webp,image/gif,.jpg,.jpeg,.png,.webp,.gif"
          :on-change="onAvatarFileChange"
        >
          <el-button type="primary">上传头像</el-button>
        </el-upload>
        <span class="avatar-hint">支持 JPG / PNG / WebP / GIF，最大 2MB；上传后可拖拽调整并圆形裁剪</span>
      </div>
    </el-card>

    <el-card class="main-card">
      <template #header>基本信息</template>
      <el-form
        ref="profileFormRef"
        :model="profileForm"
        :rules="profileRules"
        label-width="100px"
        style="max-width: 520px"
      >
        <el-form-item label="用户名">
          <el-input v-model="profileForm.username" disabled />
        </el-form-item>
        <el-form-item label="邮箱" prop="email">
          <el-input v-model="profileForm.email" />
        </el-form-item>
        <el-form-item label="姓名" prop="full_name">
          <el-input v-model="profileForm.full_name" placeholder="必填" />
        </el-form-item>
        <el-form-item label="部门" prop="department">
          <el-input v-model="profileForm.department" placeholder="部门" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="profileSaving" @click="saveProfile">保存</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card class="main-card">
      <template #header>修改密码</template>
      <el-form
        ref="pwdFormRef"
        :model="pwdForm"
        :rules="pwdRules"
        label-width="100px"
        style="max-width: 520px"
      >
        <el-form-item label="当前密码" prop="old_password">
          <el-input v-model="pwdForm.old_password" type="password" show-password autocomplete="current-password" />
        </el-form-item>
        <el-form-item label="新密码" prop="new_password">
          <el-input v-model="pwdForm.new_password" type="password" show-password autocomplete="new-password" />
        </el-form-item>
        <el-form-item label="确认新密码" prop="confirm_password">
          <el-input v-model="pwdForm.confirm_password" type="password" show-password autocomplete="new-password" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="pwdSaving" @click="savePassword">更新密码</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card class="main-card danger-card">
      <template #header>危险操作</template>
      <p class="danger-hint">注销后账号将永久删除且无法恢复（访问日志会匿名保留）。唯一超级管理员不可在此注销。</p>
      <el-button type="danger" :loading="deleteLoading" @click="deleteAccountVisible = true">注销账号</el-button>
    </el-card>

    <el-dialog v-model="deleteAccountVisible" title="确认注销账号" width="420px" destroy-on-close>
      <p class="dialog-tip">请输入当前登录密码以确认注销。</p>
      <el-input
        v-model="deletePassword"
        type="password"
        show-password
        placeholder="登录密码"
        autocomplete="current-password"
      />
      <template #footer>
        <el-button @click="deleteAccountVisible = false">取消</el-button>
        <el-button type="danger" :loading="deleteLoading" @click="confirmDeleteAccount">确认注销</el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="cropDialogVisible"
      title="裁剪圆形头像"
      width="420px"
      destroy-on-close
      class="avatar-crop-dialog"
      @closed="onCropDialogClosed"
    >
      <p class="crop-tip">拖拽图片调整位置，拖动滑块缩放；确认后以 PNG 上传。</p>
      <div class="crop-stage-wrap">
        <div
          class="crop-stage"
          @mousedown.prevent="onCropPointerDown"
        >
          <canvas
            ref="cropCanvasRef"
            class="crop-canvas"
            :width="AVATAR_CANVAS"
            :height="AVATAR_CANVAS"
          />
        </div>
      </div>
      <div class="crop-zoom">
        <span class="crop-zoom-label">缩放</span>
        <el-slider v-model="cropZoom" :min="1" :max="2.8" :step="0.02" @input="drawCropPreview" />
      </div>
      <template #footer>
        <el-button @click="cropDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="avatarLoading" @click="confirmCroppedAvatar">确定并上传</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, shallowRef, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules, type UploadInstance, type UploadProps } from 'element-plus'
import type { UploadFile, UploadRawFile } from 'element-plus'
import { authApi } from '@/api/auth'
import { useAuthStore } from '@/stores/auth'
import { goBackOrFallback } from '@/utils/navigation'
import { buildAvatarDisplaySrc } from '@/utils/avatarDisplayUrl'

const AVATAR_CANVAS = 256

const router = useRouter()
const authStore = useAuthStore()

const profileFormRef = ref<FormInstance>()
const pwdFormRef = ref<FormInstance>()
const avatarUploadRef = ref<UploadInstance>()
const cropCanvasRef = ref<HTMLCanvasElement | null>(null)

const profileSaving = ref(false)
const pwdSaving = ref(false)
const avatarLoading = ref(false)
const deleteLoading = ref(false)
const deleteAccountVisible = ref(false)
const deletePassword = ref('')

const cropDialogVisible = ref(false)
const cropZoom = ref(1)
const cropPanX = ref(0)
const cropPanY = ref(0)
const cropCoverScale = ref(1)
const cropImageEl = shallowRef<HTMLImageElement | null>(null)
let cropObjectUrl = ''

let cropDrag = false
let cropLastClientX = 0
let cropLastClientY = 0

const profileForm = reactive({
  username: '',
  email: '',
  full_name: '' as string | null,
  department: '' as string | null,
})

const pwdForm = reactive({
  old_password: '',
  new_password: '',
  confirm_password: '',
})

const profileRules: FormRules = {
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '邮箱格式不正确', trigger: 'blur' },
  ],
  full_name: [{ required: true, message: '请输入姓名', trigger: 'blur' }],
  department: [{ required: true, message: '请输入部门', trigger: 'blur' }],
}

const validateConfirmPwd = (_rule: unknown, value: string, callback: (e?: Error) => void) => {
  if (value !== pwdForm.new_password) {
    callback(new Error('两次输入的密码不一致'))
  } else {
    callback()
  }
}

const pwdRules: FormRules = {
  old_password: [{ required: true, message: '请输入当前密码', trigger: 'blur' }],
  new_password: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 8, max: 72, message: '密码长度 8～72 个字符', trigger: 'blur' },
  ],
  confirm_password: [
    { required: true, message: '请再次输入新密码', trigger: 'blur' },
    { validator: validateConfirmPwd, trigger: 'blur' },
  ],
}

const userInitial = computed(() => {
  const u = authStore.userInfo
  const name = u?.full_name || u?.username || 'U'
  return name.charAt(0).toUpperCase()
})

const avatarDisplayUrl = computed(() =>
  buildAvatarDisplaySrc(authStore.userInfo?.avatar_url, authStore.userInfo?.updated_at),
)

const goBack = () => {
  goBackOrFallback(router, '/')
}

const loadUser = async () => {
  const u = await authApi.getCurrentUser()
  authStore.setUserInfo(u)
  profileForm.username = u.username
  profileForm.email = u.email
  profileForm.full_name = u.full_name ?? ''
  profileForm.department = u.department ?? ''
}

onMounted(() => {
  loadUser().catch((e: any) => {
    ElMessage.error(e.message || '加载失败')
    router.push('/')
  })
})

const saveProfile = async () => {
  if (!profileFormRef.value) return
  await profileFormRef.value.validate()
  profileSaving.value = true
  try {
    const u = await authApi.updateCurrentUser({
      email: profileForm.email,
      full_name: (profileForm.full_name || '').trim() || null,
      department: (profileForm.department || '').trim() || null,
    })
    authStore.setUserInfo(u)
    ElMessage.success('资料已保存')
  } catch (e: any) {
    ElMessage.error(e.message || '保存失败')
  } finally {
    profileSaving.value = false
  }
}

const savePassword = async () => {
  if (!pwdFormRef.value) return
  await pwdFormRef.value.validate()
  pwdSaving.value = true
  try {
    await authApi.changePassword({
      old_password: pwdForm.old_password,
      new_password: pwdForm.new_password,
    })
    ElMessage.success('密码已更新，请牢记新密码')
    pwdForm.old_password = ''
    pwdForm.new_password = ''
    pwdForm.confirm_password = ''
    pwdFormRef.value.resetFields()
  } catch (e: any) {
    ElMessage.error(e.message || '修改失败')
  } finally {
    pwdSaving.value = false
  }
}

const ALLOWED_AVATAR_MIMES = new Set(['image/jpeg', 'image/jpg', 'image/png', 'image/webp', 'image/gif'])

const extMimeFallback = (name: string): string | null => {
  const lower = name.toLowerCase()
  if (lower.endsWith('.jpg') || lower.endsWith('.jpeg')) return 'image/jpeg'
  if (lower.endsWith('.png')) return 'image/png'
  if (lower.endsWith('.webp')) return 'image/webp'
  if (lower.endsWith('.gif')) return 'image/gif'
  return null
}

function effectiveAvatarMime(raw: UploadRawFile): string | null {
  const t = (raw.type || '').trim().toLowerCase()
  if (t && ALLOWED_AVATAR_MIMES.has(t)) return t === 'image/jpg' ? 'image/jpeg' : t
  return extMimeFallback(raw.name)
}

const validateAvatarFile = (raw: UploadRawFile): boolean => {
  const mime = effectiveAvatarMime(raw)
  if (!mime) {
    ElMessage.error('仅支持 JPG、PNG、WebP、GIF')
    return false
  }
  const max = 2 * 1024 * 1024
  if (raw.size > max) {
    ElMessage.error('图片不能超过 2MB')
    return false
  }
  return true
}

const paintAvatarCircle = (
  ctx: CanvasRenderingContext2D,
  size: number,
  img: HTMLImageElement,
  coverScale: number,
  zoom: number,
  panX: number,
  panY: number,
) => {
  const iw = img.naturalWidth
  const ih = img.naturalHeight
  ctx.clearRect(0, 0, size, size)
  ctx.save()
  ctx.beginPath()
  ctx.arc(size / 2, size / 2, size / 2, 0, Math.PI * 2)
  ctx.closePath()
  ctx.clip()
  const s = coverScale * zoom
  ctx.translate(size / 2 + panX, size / 2 + panY)
  ctx.scale(s, s)
  ctx.drawImage(img, -iw / 2, -ih / 2)
  ctx.restore()
}

const drawCropPreview = () => {
  const canvas = cropCanvasRef.value
  const img = cropImageEl.value
  if (!canvas || !img) return
  const ctx = canvas.getContext('2d')
  if (!ctx) return
  paintAvatarCircle(ctx, AVATAR_CANVAS, img, cropCoverScale.value, cropZoom.value, cropPanX.value, cropPanY.value)
}

const endCropDrag = () => {
  if (!cropDrag) return
  cropDrag = false
  window.removeEventListener('mousemove', onCropPointerMove)
  window.removeEventListener('mouseup', onCropPointerUp)
}

const onCropPointerMove = (e: MouseEvent) => {
  if (!cropDrag) return
  const dx = e.clientX - cropLastClientX
  const dy = e.clientY - cropLastClientY
  cropLastClientX = e.clientX
  cropLastClientY = e.clientY
  cropPanX.value += dx
  cropPanY.value += dy
  drawCropPreview()
}

const onCropPointerUp = () => {
  endCropDrag()
}

const onCropPointerDown = (e: MouseEvent) => {
  cropDrag = true
  cropLastClientX = e.clientX
  cropLastClientY = e.clientY
  window.addEventListener('mousemove', onCropPointerMove)
  window.addEventListener('mouseup', onCropPointerUp)
}

const onCropDialogClosed = () => {
  endCropDrag()
  if (cropObjectUrl) {
    URL.revokeObjectURL(cropObjectUrl)
    cropObjectUrl = ''
  }
  cropImageEl.value = null
  cropZoom.value = 1
  cropPanX.value = 0
  cropPanY.value = 0
}

const openCropDialog = (raw: UploadRawFile) => {
  onCropDialogClosed()
  cropObjectUrl = URL.createObjectURL(raw)
  const img = new Image()
  img.onload = () => {
    cropCoverScale.value = Math.max(AVATAR_CANVAS / img.naturalWidth, AVATAR_CANVAS / img.naturalHeight)
    cropZoom.value = 1
    cropPanX.value = 0
    cropPanY.value = 0
    cropImageEl.value = img
    cropDialogVisible.value = true
    nextTick(() => drawCropPreview())
  }
  img.onerror = () => {
    ElMessage.error('图片无法读取')
    URL.revokeObjectURL(cropObjectUrl)
    cropObjectUrl = ''
  }
  img.src = cropObjectUrl
}

const onAvatarFileChange: UploadProps['onChange'] = (uploadFile: UploadFile) => {
  const raw = uploadFile.raw
  if (!raw) return
  avatarUploadRef.value?.clearFiles()
  if (!validateAvatarFile(raw)) return
  openCropDialog(raw)
}

const confirmCroppedAvatar = async () => {
  const img = cropImageEl.value
  if (!img) {
    ElMessage.warning('请先选择图片')
    return
  }
  const canvas = document.createElement('canvas')
  canvas.width = AVATAR_CANVAS
  canvas.height = AVATAR_CANVAS
  const ctx = canvas.getContext('2d')
  if (!ctx) {
    ElMessage.error('浏览器不支持裁剪')
    return
  }
  paintAvatarCircle(ctx, AVATAR_CANVAS, img, cropCoverScale.value, cropZoom.value, cropPanX.value, cropPanY.value)

  avatarLoading.value = true
  try {
    const file = await new Promise<File>((resolve, reject) => {
      canvas.toBlob(
        (blob) => {
          if (!blob) {
            reject(new Error('导出失败'))
            return
          }
          resolve(new File([blob], 'avatar.png', { type: 'image/png' }))
        },
        'image/png',
        0.92,
      )
    })
    if (file.size > 2 * 1024 * 1024) {
      ElMessage.error('裁剪后仍超过 2MB，请换一张较小的原图或缩小缩放')
      return
    }
    const u = await authApi.uploadAvatar(file)
    authStore.setUserInfo(u)
    ElMessage.success('头像已更新')
    cropDialogVisible.value = false
  } catch (e: any) {
    ElMessage.error(e.message || '上传失败')
  } finally {
    avatarLoading.value = false
  }
}

const confirmDeleteAccount = async () => {
  const pwd = deletePassword.value.trim()
  if (!pwd) {
    ElMessage.warning('请输入密码')
    return
  }
  deleteLoading.value = true
  try {
    await authApi.deleteAccount({ password: pwd })
    ElMessage.success('账号已注销')
    deleteAccountVisible.value = false
    authStore.clearTokens()
    router.push('/login')
  } catch (e: any) {
    ElMessage.error(e.message || '注销失败')
  } finally {
    deleteLoading.value = false
    deletePassword.value = ''
  }
}
</script>

<style scoped>
.profile-page {
  padding: 20px;
}

.page-header-title {
  font-size: 18px;
  font-weight: bold;
  color: #303133;
}

.main-card {
  margin-top: 20px;
}

.avatar-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 16px;
}

.avatar-hint {
  color: #909399;
  font-size: 13px;
}

.danger-card :deep(.el-card__header) {
  color: #f56c6c;
}

.danger-hint {
  color: #909399;
  font-size: 13px;
  margin: 0 0 16px;
  line-height: 1.5;
}

.dialog-tip {
  margin: 0 0 12px;
  color: #606266;
  font-size: 14px;
}

.crop-tip {
  margin: 0 0 12px;
  color: #606266;
  font-size: 13px;
  line-height: 1.5;
}

.crop-stage-wrap {
  display: flex;
  justify-content: center;
  margin-bottom: 8px;
}

.crop-stage {
  border-radius: 50%;
  box-shadow: 0 0 0 2px #dcdfe6 inset;
  cursor: grab;
  line-height: 0;
  user-select: none;
}

.crop-stage:active {
  cursor: grabbing;
}

.crop-canvas {
  display: block;
  width: 280px;
  height: 280px;
  border-radius: 50%;
}

.crop-zoom {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 8px;
}

.crop-zoom-label {
  flex: 0 0 36px;
  color: #606266;
  font-size: 13px;
}

.crop-zoom :deep(.el-slider) {
  flex: 1;
}
</style>
