<template>
  <div class="data-secure-manage-panel" v-loading="loading">
    <el-card shadow="never" class="ds-space-bar">
      <template #header>项目空间</template>
      <el-select
        v-model="selectedSpaceId"
        style="width: 100%; max-width: 480px"
        placeholder="请选择项目空间"
        filterable
        @change="onSpaceChange"
      >
        <el-option v-for="space in spaces" :key="space.id" :label="space.name" :value="space.id" />
      </el-select>
      <p class="section-hint space-bar-hint">
        顶栏所选为问卷与分步填报的当前工作空间；「我的填报与导出」内各列表默认随该空间；「填报工单」内的过审导出可单独选择导出目标项目空间。
      </p>
    </el-card>

    <el-tabs v-model="mainTab" class="ds-main-tabs" @tab-change="onMainTabChange">
      <el-tab-pane label="分步填报" name="fill">
        <div class="ds-fill-pane">
          <div class="ds-focus-toolbar">
            <el-button v-if="canGoBack" text type="primary" @click="goBackStep">返回上一步</el-button>
            <span class="toolbar-hint">当前为分步填报，仅显示当前步骤；可通过「返回上一步」回退修订。工单列表与导出请打开「我的填报与导出」页签。</span>
          </div>

          <el-alert
            v-show="focusMode === 'questionnaire'"
            type="info"
            :closable="false"
            show-icon
            title="请先完成下方「相关性判定填报」。仅当判定结果为「相关」后，才可填报数据字段（数据字段 + 其他信息）；自动分类分级与安全要求仅按去重后的数据字段主表行计算，与填报中的其他信息无关。"
          />

          <el-card v-show="focusMode === 'questionnaire'" shadow="never">
            <template #header>相关性判定填报</template>
            <el-form label-position="top">
        <el-form-item label="功能名称">
          <template v-if="businessFunctionConfigured">
            <el-select
              v-model="form.function_name"
              filterable
              clearable
              style="width: 100%; max-width: 560px"
              placeholder="从「业务功能」可选值中选择，可输入关键字筛选"
            >
              <el-option v-for="op in businessFunctionOptions" :key="op" :label="op" :value="op" />
            </el-select>
            <p class="section-hint field-fn-hint">
              选项来自填报表单中「业务功能」列的允许值与主表已填该列取值的汇总，与数据字段填报里「业务功能」一致，避免同一功能多种叫法。
            </p>
          </template>
          <template v-else>
            <el-input
              v-model="form.function_name"
              maxlength="500"
              show-word-limit
              placeholder="当前空间尚未配置「业务功能」列时可自由填写；建议负责人在管理页「填报表单字段」中新增 field_key 为 business_function、列名为「业务功能」的字段"
            />
          </template>
          <el-link type="primary" class="field-request-hint" @click.prevent="openBfOptionRequestDialog">
            列表中没有我的业务功能？点击申请新增
          </el-link>
        </el-form-item>
        <el-form-item v-for="q in questions" :key="q.id">
          <template #label>
            <span class="form-label-with-tip">
              <span>{{ q.title }}</span>
              <el-link
                v-if="(q.help_text || '').trim()"
                type="primary"
                class="question-help-link"
                @click.prevent="openQuestionHelpDialog(q)"
              >
                查看说明
              </el-link>
            </span>
          </template>
          <el-radio-group v-model="answersMap[q.id]">
            <el-radio :label="true">是</el-radio>
            <el-radio :label="false">否</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-button type="primary" :loading="submitting" @click="submitAssessment">提交判定</el-button>
      </el-form>
      <el-alert v-if="lastResult && focusMode === 'questionnaire'" class="result-alert" type="success" :closable="false" :title="lastResult.result_summary" />
    </el-card>

    <el-card v-if="focusMode === 'done'" shadow="never" class="done-card">
      <template #header>本次工单</template>
      <el-alert
        v-if="lastResult"
        type="success"
        :closable="false"
        show-icon
        :title="lastResult.is_related ? '字段填报已提交，等待工具负责人审批。' : '问卷判定为「不相关」，本次无需字段填报。'"
      />
      <p v-if="lastResult" class="section-hint">{{ lastResult.result_summary }}</p>
      <el-button type="primary" class="new-ticket-btn" @click="startNewTicket">开始新的填报</el-button>
    </el-card>

    <el-card v-show="focusMode === 'usage' && usageReportingUnlocked" shadow="never">
      <template #header>数据字段填报（数据字段 + 其他信息）</template>
      <p class="section-hint">
        下方选项来自字段主表；每个字段需按工具负责人配置的「其他信息」列填写。无须单独填写功能说明（功能相关说明应体现在其他信息配置列中）。
      </p>
      <el-form label-position="top">
        <el-form-item label="选择数据字段">
          <el-select
            v-model="usageForm.field_entry_ids"
            multiple
            filterable
            remote
            reserve-keyword
            style="width: 100%"
            :remote-method="searchCatalog"
            :loading="catalogLoading"
            placeholder="输入关键字模糊搜索字段"
            @change="onUsageFieldSelectionChange"
          >
            <el-option
              v-for="item in catalogOptions"
              :key="item.id"
              :label="item.field_name"
              :value="item.id"
            />
          </el-select>
        </el-form-item>
        <template v-for="eid in usageForm.field_entry_ids" :key="eid">
          <el-divider content-position="left">{{ catalogLabelById(eid) }}</el-divider>
          <dynamic-field-inputs
            v-model="usageExtrasState[eid]"
            :fields="usageDynamicFields"
          />
        </template>
        <el-form-item label="备注（选填）">
          <el-input v-model="usageForm.notes" type="textarea" :rows="2" maxlength="1000" show-word-limit placeholder="最多 1000 字" />
        </el-form-item>
        <el-link type="primary" class="field-request-hint" @click.prevent="openFieldRequestDialog">
          没有找到功能涉及的数据字段？点击此处申请字段新增
        </el-link>
        <el-alert
          v-if="fieldUsageAlreadySubmitted"
          type="info"
          :closable="false"
          show-icon
          class="section-alert"
          title="本问卷已提交过字段填报，不可再次提交。请返回修改问卷并重新提交，或点击「开始新的填报」开启新工单。"
        />
        <div class="usage-submit-wrap">
          <el-button type="primary" :loading="usageSubmitting" :disabled="fieldUsageAlreadySubmitted" @click="submitUsageReport">
            提交填报
          </el-button>
        </div>
      </el-form>
      <el-divider />
      <el-table :data="usageReports" stripe>
        <el-table-column prop="submitted_at" label="填报时间" width="180">
          <template #default="scope">{{ formatDate(scope.row.submitted_at) }}</template>
        </el-table-column>
        <el-table-column prop="function_name" label="摘要" min-width="140" />
        <el-table-column label="涉及字段" min-width="260">
          <template #default="scope">{{ (scope.row.field_names || []).join('，') }}</template>
        </el-table-column>
        <el-table-column prop="notes" label="备注" min-width="200" />
      </el-table>
    </el-card>

    <el-card v-show="focusMode === 'usage' && !usageReportingUnlocked" shadow="never" class="locked-card">
      <template #header>数据字段填报</template>
      <el-alert
        type="warning"
        :closable="false"
        show-icon
        title="请先在「分步填报」中完成相关性判定，且最近一次有效记录需为「相关」后，方可填报数据字段。"
      />
      <el-link type="primary" class="field-request-hint field-request-hint--locked" @click.prevent="openFieldRequestDialog">
        没有找到功能涉及的数据字段？点击此处申请字段新增
      </el-link>
    </el-card>

        </div>
      </el-tab-pane>

      <el-tab-pane label="我的填报与导出" name="mine">
        <div class="ds-mine-pane" v-loading="mineTabLoading">
          <el-alert
            type="info"
            :closable="false"
            show-icon
            class="section-alert"
            title="在此集中查看本人问卷工单、字段填报与字段新增申请；「填报工单」内可导出本人审批通过的过审大表（CSV）。负责人导出全空间过审数据请在管理页操作。"
          />
          <div class="mine-toolbar">
            <el-button type="primary" plain :disabled="!selectedSpaceId" @click="refreshMineTab">刷新列表</el-button>
          </div>

          <el-tabs v-model="mineInnerTab" class="ds-mine-inner-tabs">
            <el-tab-pane label="填报工单" name="orders">
              <el-tabs v-model="mineOrdersInnerTab" class="ds-mine-inner-tabs">
                <el-tab-pane label="工单记录" name="wo-list">
                  <el-card shadow="never">
                    <template #header>填报工单记录（本人）</template>
                    <p class="section-hint">每次问卷提交形成一条工单；若判定为「相关」并提交字段填报，则合并显示审批状态。</p>
                    <el-table :data="workOrders" stripe empty-text="暂无记录">
                      <el-table-column prop="questionnaire_submitted_at" label="问卷提交时间" width="180">
                        <template #default="scope">{{ formatDate(scope.row.questionnaire_submitted_at) }}</template>
                      </el-table-column>
                      <el-table-column prop="function_name" label="功能名称" min-width="160" />
                      <el-table-column label="问卷结果" width="100">
                        <template #default="scope">
                          <el-tag :type="scope.row.is_related ? 'warning' : 'info'">{{ scope.row.is_related ? '相关' : '不相关' }}</el-tag>
                        </template>
                      </el-table-column>
                      <el-table-column label="字段填报" width="110">
                        <template #default="scope">{{ scope.row.field_usage_report_id ? '已提交' : '—' }}</template>
                      </el-table-column>
                      <el-table-column label="审批" width="120">
                        <template #default="scope">
                          <template v-if="!scope.row.field_usage_report_id">—</template>
                          <el-tag v-else-if="scope.row.review_status === 'pending'" type="warning">待审批</el-tag>
                          <el-tag v-else-if="scope.row.review_status === 'approved'" type="success">已通过</el-tag>
                          <el-tag v-else-if="scope.row.review_status === 'rejected'" type="info">已驳回</el-tag>
                          <span v-else>—</span>
                        </template>
                      </el-table-column>
                    </el-table>
                    <div class="table-pagination">
                      <el-pagination
                        v-model:current-page="woPage"
                        v-model:page-size="woPageSize"
                        :total="woTotal"
                        :page-sizes="[10, 20, 50]"
                        layout="total, sizes, prev, pager, next"
                        @current-change="loadWorkOrders"
                        @size-change="onWoPageSizeChange"
                      />
                    </div>
                  </el-card>
                </el-tab-pane>
                <el-tab-pane label="过审导出" name="wo-export">
                  <el-card shadow="never">
                    <template #header>导出本人过审大表（CSV）</template>
                    <p class="section-hint">
                      请选择<strong>导出目标项目空间</strong>（可与顶栏当前工作空间不同）。导出该空间内、您本人提交的且<strong>审批通过</strong>的字段填报合并行（含分类分级与安全要求配置摘要）。可按「其他信息」多选列 key、多选「值包含」关键词筛选（列 OR、关键词 OR；未选关键词时仅要求所选列在快照中存在）。
                    </p>
                    <el-form label-position="top" class="export-filter-form" @submit.prevent>
                      <el-form-item label="导出项目空间" required>
                        <el-select v-model="mineExportSpaceId" filterable placeholder="请选择项目空间" style="width: 100%; max-width: 400px">
                          <el-option v-for="space in spaces" :key="space.id" :label="space.name" :value="space.id" />
                        </el-select>
                      </el-form-item>
                      <el-form-item label="筛选字段 key（选填，可多选）">
                        <el-select
                          v-model="mineExportFilterKeys"
                          multiple
                          filterable
                          clearable
                          allow-create
                          default-first-option
                          collapse-tags
                          collapse-tags-tooltip
                          placeholder="对应其他信息 JSON 中的键名（可多选，OR）"
                          style="width: 100%"
                        >
                          <el-option
                            v-for="op in mineExportFieldKeyOptions"
                            :key="op.value"
                            :label="op.label"
                            :value="op.value"
                          />
                        </el-select>
                      </el-form-item>
                      <el-form-item label="值包含（选填，可多选）">
                        <el-select
                          v-model="mineExportFilterContainsList"
                          multiple
                          filterable
                          clearable
                          allow-create
                          default-first-option
                          collapse-tags
                          collapse-tags-tooltip
                          placeholder="关键词 OR；不选则仅按列存在性筛选"
                          style="width: 100%"
                        />
                      </el-form-item>
                    </el-form>
                    <el-button type="primary" plain :disabled="!mineExportSpaceId" :loading="exportMineLoading" @click="exportMineApproved">
                      导出 CSV
                    </el-button>
                  </el-card>
                </el-tab-pane>
              </el-tabs>
            </el-tab-pane>

            <el-tab-pane label="字段填报记录" name="usage">
              <el-card shadow="never">
                <template #header>我的字段填报</template>
                <el-table :data="mineUsageList" stripe empty-text="暂无记录">
                  <el-table-column prop="submitted_at" label="填报时间" width="180">
                    <template #default="scope">{{ formatDate(scope.row.submitted_at) }}</template>
                  </el-table-column>
                  <el-table-column prop="function_name" label="摘要" min-width="140" />
                  <el-table-column label="涉及字段" min-width="220">
                    <template #default="scope">{{ (scope.row.field_names || []).join('，') }}</template>
                  </el-table-column>
                  <el-table-column prop="notes" label="备注" min-width="160" show-overflow-tooltip />
                  <el-table-column label="审批" width="110">
                    <template #default="scope">
                      <el-tag v-if="scope.row.review_status === 'pending'" type="warning">待审批</el-tag>
                      <el-tag v-else-if="scope.row.review_status === 'approved'" type="success">已通过</el-tag>
                      <el-tag v-else-if="scope.row.review_status === 'rejected'" type="info">已驳回</el-tag>
                      <span v-else>—</span>
                    </template>
                  </el-table-column>
                </el-table>
                <div class="table-pagination">
                  <el-pagination
                    v-model:current-page="mineUrPage"
                    v-model:page-size="mineUrPageSize"
                    :total="mineUrTotal"
                    :page-sizes="[10, 20, 50]"
                    layout="total, sizes, prev, pager, next"
                    @current-change="loadMineUsageReports"
                    @size-change="onMineUrPageSizeChange"
                  />
                </div>
              </el-card>
            </el-tab-pane>

            <el-tab-pane label="字段新增申请" name="fieldreq">
              <el-tabs v-model="mineFieldreqInnerTab" class="ds-mine-inner-tabs">
                <el-tab-pane label="数据字段申请" name="datafield">
                  <el-card shadow="never">
                    <template #header>我的数据字段新增申请</template>
                    <el-table :data="mineFieldReqList" stripe empty-text="暂无记录">
                      <el-table-column prop="created_at" label="申请时间" width="180">
                        <template #default="scope">{{ formatDate(scope.row.created_at) }}</template>
                      </el-table-column>
                      <el-table-column prop="field_name" label="数据字段" min-width="180" />
                      <el-table-column label="状态" width="120">
                        <template #default="scope">
                          <el-tag :type="scope.row.status === 'pending' ? 'warning' : scope.row.status === 'approved' ? 'success' : 'info'">
                            {{ scope.row.status === 'pending' ? '待审核' : scope.row.status === 'approved' ? '已通过' : '已驳回' }}
                          </el-tag>
                        </template>
                      </el-table-column>
                      <el-table-column prop="review_notes" label="审核备注" min-width="220" show-overflow-tooltip />
                    </el-table>
                    <div class="table-pagination">
                      <el-pagination
                        v-model:current-page="mineFrPage"
                        v-model:page-size="mineFrPageSize"
                        :total="mineFrTotal"
                        :page-sizes="[10, 20, 50]"
                        layout="total, sizes, prev, pager, next"
                        @current-change="loadMineFieldRequests"
                        @size-change="onMineFrPageSizeChange"
                      />
                    </div>
                  </el-card>
                </el-tab-pane>
                <el-tab-pane label="业务功能选项申请" name="bfopt">
                  <el-card shadow="never">
                    <template #header>我的业务功能选项申请</template>
                    <el-table :data="mineBfReqList" stripe empty-text="暂无记录">
                      <el-table-column prop="created_at" label="申请时间" width="180">
                        <template #default="scope">{{ formatDate(scope.row.created_at) }}</template>
                      </el-table-column>
                      <el-table-column prop="proposed_option" label="申请选项" min-width="160" />
                      <el-table-column label="状态" width="120">
                        <template #default="scope">
                          <el-tag :type="scope.row.status === 'pending' ? 'warning' : scope.row.status === 'approved' ? 'success' : 'info'">
                            {{ scope.row.status === 'pending' ? '待审核' : scope.row.status === 'approved' ? '已通过' : '已驳回' }}
                          </el-tag>
                        </template>
                      </el-table-column>
                      <el-table-column prop="review_notes" label="审核备注" min-width="220" show-overflow-tooltip />
                    </el-table>
                    <div class="table-pagination">
                      <el-pagination
                        v-model:current-page="mineBfPage"
                        v-model:page-size="mineBfPageSize"
                        :total="mineBfTotal"
                        :page-sizes="[10, 20, 50]"
                        layout="total, sizes, prev, pager, next"
                        @current-change="loadMineBfOptionRequests"
                        @size-change="onMineBfPageSizeChange"
                      />
                    </div>
                  </el-card>
                </el-tab-pane>
              </el-tabs>
            </el-tab-pane>

            <el-tab-pane label="分类分级参考" name="classification">
              <el-card shadow="never">
                <template #header>分类分级结果（只读）</template>
                <el-alert
                  type="info"
                  :closable="false"
                  class="section-alert"
                  title="展示的分类分级与安全要求命中与当前空间数据字段主表相关；同一字段被多次填报不会重复计算，其他信息不影响自动规则与安全要求表达式求值结果。"
                  show-icon
                />
                <el-table :data="classificationResults" stripe empty-text="暂无数据">
                  <el-table-column prop="field_name_snapshot" label="数据字段" min-width="200" />
                  <el-table-column label="来源" width="90">
                    <template #default="scope">
                      <el-tag size="small" :type="scope.row.source === 'manual' ? 'warning' : 'success'">
                        {{ scope.row.source === 'manual' ? '人工' : '自动' }}
                      </el-tag>
                    </template>
                  </el-table-column>
                  <el-table-column prop="category" label="展示分类" width="120" />
                  <el-table-column prop="level" label="展示分级" width="100" />
                  <el-table-column label="自动分类/分级" width="150">
                    <template #default="scope">
                      {{ scope.row.auto_category }} / {{ scope.row.auto_level }}
                    </template>
                  </el-table-column>
                  <el-table-column label="自动依据" width="120">
                    <template #default="scope">
                      {{
                        scope.row.auto_match_source === 'matrix'
                          ? '显式矩阵'
                          : scope.row.auto_match_source === 'keyword'
                            ? '关键词'
                            : scope.row.auto_match_source === 'default'
                              ? '默认'
                              : scope.row.auto_match_source === 'structured'
                                ? '分类分级和要求治理'
                                : '—'
                      }}
                    </template>
                  </el-table-column>
                  <el-table-column prop="auto_hit_summary" label="命中说明" min-width="240" show-overflow-tooltip />
                  <el-table-column prop="updated_at" label="更新时间" width="170">
                    <template #default="scope">{{ formatDate(scope.row.updated_at) }}</template>
                  </el-table-column>
                </el-table>
              </el-card>
            </el-tab-pane>
          </el-tabs>

          <el-alert v-if="mineTabLoadError" type="error" :closable="false" show-icon :title="mineTabLoadError" />
        </div>
      </el-tab-pane>
    </el-tabs>

    <el-alert v-if="loadError" type="error" :closable="false" show-icon class="panel-load-error" :title="loadError" />

    <el-dialog
      v-model="questionHelpDialogVisible"
      :title="questionHelpTitle || '题目说明'"
      width="760px"
      append-to-body
    >
      <div class="question-help-content markdown-body" v-html="questionHelpHtml"></div>
      <template #footer>
        <el-button type="primary" @click="questionHelpDialogVisible = false">我知道了</el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="bfOptionRequestDialogVisible"
      title="业务功能选项新增申请"
      width="480px"
      class="field-request-dialog"
      append-to-body
      @closed="onBfOptionRequestDialogClosed"
    >
      <p class="section-hint dialog-hint">
        填写希望在「功能名称」下拉中出现的业务功能名称。审核通过后，工具负责人将把该名称加入「业务功能」填报字段的允许值。
      </p>
      <el-form label-position="top" @submit.prevent>
        <el-form-item label="申请选项名称" required>
          <el-input
            v-model="bfOptionRequestForm.proposed_option"
            maxlength="200"
            show-word-limit
            placeholder="与上线功能对外称呼尽量一致"
            @keyup.enter="submitBfOptionRequest"
          />
        </el-form-item>
        <el-form-item label="说明（选填）">
          <el-input v-model="bfOptionRequestForm.reason" type="textarea" :rows="2" maxlength="1000" show-word-limit />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="bfOptionRequestDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="bfOptionRequestSubmitting" @click="submitBfOptionRequest">提交申请</el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="fieldRequestDialogVisible"
      title="数据字段新增申请"
      width="480px"
      class="field-request-dialog"
      append-to-body
      @closed="onFieldRequestDialogClosed"
    >
      <p class="section-hint dialog-hint">
        填写待新增的「数据字段」名称（建议与代码或库表字段一致）。审核通过后，工具负责人将在管理页主表中维护「其他信息」等列。
      </p>
      <el-form label-position="top" @submit.prevent>
        <el-form-item label="数据字段名称" required>
          <el-input
            v-model="fieldRequestForm.field_name"
            maxlength="200"
            show-word-limit
            placeholder="例如：user_device_fingerprint"
            @keyup.enter="submitFieldRequest"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="fieldRequestDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="requestSubmitting" @click="submitFieldRequest">提交申请</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { toolsApi } from '@/api/tools'
import { formatDateTime as formatDate } from '@/utils/datetime'
import { renderMarkdown } from '@/utils/markdown'
import { downloadApprovedConsolidatedCsv } from '@/utils/csvExport'
import type {
  DataSecureAssessmentSubmission,
  DataSecureBusinessFunctionOptionRequest,
  DataSecureFieldCatalogEntry,
  DataSecureClassificationResult,
  DataSecureFieldRequest,
  DataSecureFieldUsageReport,
  DataSecureProjectSpace,
  DataSecureQuestion,
  DataSecureWorkOrderRow,
  DynamicFormValues,
  FormFieldConfigItem
} from '@/api/types'
import DynamicFieldInputs from '@/components/form-config/DynamicFieldInputs.vue'

const props = defineProps<{ toolId: number }>()

type FocusMode = 'questionnaire' | 'usage' | 'done'

const loading = ref(false)
const loadError = ref('')
const mainTab = ref('fill')
const mineTabLoading = ref(false)
const mineTabLoadError = ref('')
const mineUrPage = ref(1)
const mineUrPageSize = ref(20)
const mineUrTotal = ref(0)
const mineUsageList = ref<DataSecureFieldUsageReport[]>([])
const mineFrPage = ref(1)
const mineFrPageSize = ref(20)
const mineFrTotal = ref(0)
const mineFieldReqList = ref<DataSecureFieldRequest[]>([])
const mineBfPage = ref(1)
const mineBfPageSize = ref(20)
const mineBfTotal = ref(0)
const mineBfReqList = ref<DataSecureBusinessFunctionOptionRequest[]>([])
const mineExportFilterKeys = ref<string[]>([])
const mineExportFilterContainsList = ref<string[]>([])
/** 过审大表导出目标空间（可与顶栏「当前工作空间」不同） */
const mineExportSpaceId = ref<number | null>(null)
const mineInnerTab = ref('orders')
/** 「填报工单」内：工单列表 / 过审导出 */
const mineOrdersInnerTab = ref('wo-list')
/** 「字段新增申请」内：数据字段 / 业务功能选项 */
const mineFieldreqInnerTab = ref('datafield')
const focusMode = ref<FocusMode>('questionnaire')
/** 当前问卷是否已成功提交过字段填报（同 assessment 不可重复提交） */
const fieldUsageAlreadySubmitted = ref(false)
const lastAssessmentId = ref<number | null>(null)

const canGoBack = computed(() => focusMode.value !== 'questionnaire')

const goBackStep = () => {
  if (focusMode.value === 'usage') {
    focusMode.value = 'questionnaire'
    void loadBusinessFunctionOptions()
    return
  }
  if (focusMode.value === 'done') {
    if (lastResult.value?.is_related) {
      focusMode.value = 'usage'
    } else {
      focusMode.value = 'questionnaire'
      void loadBusinessFunctionOptions()
    }
  }
}
const spaces = ref<DataSecureProjectSpace[]>([])
const selectedSpaceId = ref<number | null>(null)
const questions = ref<DataSecureQuestion[]>([])
const answersMap = reactive<Record<number, boolean>>({})
const workOrders = ref<DataSecureWorkOrderRow[]>([])
const woPage = ref(1)
const woPageSize = ref(20)
const woTotal = ref(0)
const exportMineLoading = ref(false)
const usageReportingUnlocked = ref(false)
const fieldRequestDialogVisible = ref(false)
const bfOptionRequestDialogVisible = ref(false)
const bfOptionRequestSubmitting = ref(false)
const businessFunctionConfigured = ref(false)
const businessFunctionOptions = ref<string[]>([])
const catalogOptions = ref<DataSecureFieldCatalogEntry[]>([])
const usageReports = ref<DataSecureFieldUsageReport[]>([])
const classificationResults = ref<DataSecureClassificationResult[]>([])
const lifecycleFieldsUsage = ref<FormFieldConfigItem[]>([])
const catalogLoading = ref(false)
const submitting = ref(false)
const lastResult = ref<DataSecureAssessmentSubmission | null>(null)
const requestSubmitting = ref(false)
const usageSubmitting = ref(false)
const form = reactive({
  function_name: ''
})
const fieldRequestForm = reactive<{
  field_name: string
}>({
  field_name: ''
})
const bfOptionRequestForm = reactive<{
  proposed_option: string
  reason: string
}>({
  proposed_option: '',
  reason: ''
})
const usageForm = reactive<{
  field_entry_ids: number[]
  notes: string
}>({
  field_entry_ids: [],
  notes: ''
})

/** 每个主表行 id -> 填报时的其他信息 */
const usageExtrasState = reactive<Record<number, DynamicFormValues>>({})

const usageDynamicFields = computed(() =>
  lifecycleFieldsUsage.value.filter((item) => !item.is_builtin || item.field_key === 'business_function')
)
const mineExportFieldKeyOptions = computed(() =>
  usageDynamicFields.value.map((item) => ({ label: `${item.label} (${item.field_key})`, value: item.field_key }))
)
const questionHelpDialogVisible = ref(false)
const questionHelpTitle = ref('')
const questionHelpHtml = ref('')

const catalogLabelById = (id: number) => {
  const row = catalogOptions.value.find((x) => x.id === id)
  return row ? row.field_name : `字段 #${id}`
}

const openQuestionHelpDialog = (question: DataSecureQuestion) => {
  questionHelpTitle.value = `${question.title} - 说明`
  questionHelpHtml.value = renderMarkdown(question.help_text || '')
  questionHelpDialogVisible.value = true
}

const refreshUsageUnlock = async () => {
  if (!selectedSpaceId.value) {
    usageReportingUnlocked.value = false
    return
  }
  const res = await toolsApi.getDataSecureAssessments(props.toolId, selectedSpaceId.value, 0, 500)
  const latest = (res.items || [])[0]
  usageReportingUnlocked.value = Boolean(latest?.is_related)
}

const loadSpaces = async () => {
  const res = await toolsApi.getDataSecureProjectSpaces(props.toolId, 0, 100)
  spaces.value = res.items.filter((x) => x.is_active)
  const ids = new Set(spaces.value.map((x) => x.id))
  if (selectedSpaceId.value != null && !ids.has(selectedSpaceId.value)) {
    selectedSpaceId.value = spaces.value.length ? spaces.value[0].id : null
  }
  if (selectedSpaceId.value == null && spaces.value.length) {
    selectedSpaceId.value = spaces.value[0].id
  }
  if (mineExportSpaceId.value != null && !ids.has(mineExportSpaceId.value)) {
    mineExportSpaceId.value = selectedSpaceId.value
  }
  if (mineExportSpaceId.value == null) {
    mineExportSpaceId.value = selectedSpaceId.value
  }
}

const loadLifecycleUsageFields = async () => {
  if (!selectedSpaceId.value) {
    lifecycleFieldsUsage.value = []
    return
  }
  const res = await toolsApi.getDataSecureLifecycleFieldConfigs(props.toolId, selectedSpaceId.value)
  lifecycleFieldsUsage.value = res.items
}

const loadBusinessFunctionOptions = async () => {
  if (!selectedSpaceId.value) {
    businessFunctionConfigured.value = false
    businessFunctionOptions.value = []
    return
  }
  try {
    const res = await toolsApi.getDataSecureBusinessFunctionOptions(props.toolId, selectedSpaceId.value)
    businessFunctionConfigured.value = res.business_function_configured
    businessFunctionOptions.value = res.options || []
  } catch {
    businessFunctionConfigured.value = false
    businessFunctionOptions.value = []
  }
}

const loadQuestions = async () => {
  if (!selectedSpaceId.value) return
  const res = await toolsApi.getDataSecureQuestions(props.toolId, selectedSpaceId.value, 0, 200)
  questions.value = res.items.filter((x) => x.is_active).sort((a, b) => a.sort_order - b.sort_order)
  Object.keys(answersMap).forEach((k) => delete answersMap[Number(k)])
}

const loadWorkOrders = async () => {
  const res = await toolsApi.getDataSecureWorkOrders(props.toolId, {
    project_space_id: selectedSpaceId.value || undefined,
    skip: (woPage.value - 1) * woPageSize.value,
    limit: woPageSize.value,
    mine: true
  })
  workOrders.value = res.items
  woTotal.value = res.total
}

const loadMineUsageReports = async () => {
  if (!selectedSpaceId.value) {
    mineUsageList.value = []
    mineUrTotal.value = 0
    return
  }
  const res = await toolsApi.getDataSecureFieldUsageReports(props.toolId, {
    project_space_id: selectedSpaceId.value,
    skip: (mineUrPage.value - 1) * mineUrPageSize.value,
    limit: mineUrPageSize.value
  })
  mineUsageList.value = res.items
  mineUrTotal.value = res.total
}

const onMineUrPageSizeChange = async (size: number) => {
  mineUrPageSize.value = size
  mineUrPage.value = 1
  await loadMineUsageReports()
}

const loadMineFieldRequests = async () => {
  const res = await toolsApi.getDataSecureFieldRequests(props.toolId, {
    project_space_id: selectedSpaceId.value || undefined,
    skip: (mineFrPage.value - 1) * mineFrPageSize.value,
    limit: mineFrPageSize.value
  })
  mineFieldReqList.value = res.items
  mineFrTotal.value = res.total
}

const onMineFrPageSizeChange = async (size: number) => {
  mineFrPageSize.value = size
  mineFrPage.value = 1
  await loadMineFieldRequests()
}

const loadMineBfOptionRequests = async () => {
  const res = await toolsApi.getDataSecureBusinessFunctionOptionRequests(props.toolId, {
    project_space_id: selectedSpaceId.value || undefined,
    skip: (mineBfPage.value - 1) * mineBfPageSize.value,
    limit: mineBfPageSize.value
  })
  mineBfReqList.value = res.items
  mineBfTotal.value = res.total
}

const onMineBfPageSizeChange = async (size: number) => {
  mineBfPageSize.value = size
  mineBfPage.value = 1
  await loadMineBfOptionRequests()
}

const refreshMineTab = async () => {
  if (!selectedSpaceId.value) {
    ElMessage.warning('请先选择项目空间')
    return
  }
  mineTabLoading.value = true
  mineTabLoadError.value = ''
  try {
    woPage.value = 1
    await loadWorkOrders()
    mineUrPage.value = 1
    await loadMineUsageReports()
    mineFrPage.value = 1
    await loadMineFieldRequests()
    mineBfPage.value = 1
    await loadMineBfOptionRequests()
    await loadClassificationResults()
  } catch (e: any) {
    const msg = e?.message || '加载失败'
    mineTabLoadError.value = msg
    ElMessage.error(msg)
  } finally {
    mineTabLoading.value = false
  }
}

const onMainTabChange = (name: string | number) => {
  if (String(name) === 'mine') {
    void refreshMineTab()
  }
}

const onWoPageSizeChange = async (size: number) => {
  woPageSize.value = size
  woPage.value = 1
  await loadWorkOrders()
}

const startNewTicket = async () => {
  focusMode.value = 'questionnaire'
  fieldUsageAlreadySubmitted.value = false
  lastResult.value = null
  lastAssessmentId.value = null
  form.function_name = ''
  Object.keys(answersMap).forEach((k) => delete answersMap[Number(k)])
  await loadQuestions()
  await loadBusinessFunctionOptions()
  await loadWorkOrders()
  await loadMineUsageReports()
}

const exportMineApproved = async () => {
  if (!mineExportSpaceId.value) return ElMessage.warning('请选择导出目标项目空间')
  exportMineLoading.value = true
  try {
    const fk = mineExportFilterKeys.value.map((x) => String(x).trim()).filter(Boolean)
    const fv = mineExportFilterContainsList.value.map((x) => String(x).trim()).filter(Boolean)
    const res = await toolsApi.exportDataSecureApprovedConsolidated(props.toolId, {
      project_space_id: mineExportSpaceId.value,
      mine: true,
      filter_field_key: fk.length ? fk : undefined,
      filter_value_contains: fv.length ? fv : undefined
    })
    downloadApprovedConsolidatedCsv(`本人过审填报汇总-空间${mineExportSpaceId.value}.csv`, res.items)
    ElMessage.success('已开始下载')
  } catch (error: any) {
    ElMessage.error(error?.message || '导出失败')
  } finally {
    exportMineLoading.value = false
  }
}

const openFieldRequestDialog = () => {
  if (!selectedSpaceId.value) {
    ElMessage.warning('请先选择项目空间')
    return
  }
  fieldRequestForm.field_name = ''
  fieldRequestDialogVisible.value = true
}

const onFieldRequestDialogClosed = () => {
  fieldRequestForm.field_name = ''
}

const openBfOptionRequestDialog = () => {
  if (!selectedSpaceId.value) {
    ElMessage.warning('请先选择项目空间')
    return
  }
  bfOptionRequestForm.proposed_option = ''
  bfOptionRequestForm.reason = ''
  bfOptionRequestDialogVisible.value = true
}

const onBfOptionRequestDialogClosed = () => {
  bfOptionRequestForm.proposed_option = ''
  bfOptionRequestForm.reason = ''
}

const submitBfOptionRequest = async () => {
  if (!selectedSpaceId.value) return ElMessage.warning('请先选择项目空间')
  const prop = bfOptionRequestForm.proposed_option.trim()
  if (!prop) return ElMessage.warning('请填写申请选项名称')
  bfOptionRequestSubmitting.value = true
  try {
    await toolsApi.createDataSecureBusinessFunctionOptionRequest(props.toolId, {
      project_space_id: selectedSpaceId.value,
      proposed_option: prop,
      reason: bfOptionRequestForm.reason.trim() || undefined
    })
    ElMessage.success('业务功能选项申请已提交，请等待工具负责人审核')
    bfOptionRequestDialogVisible.value = false
    await loadMineBfOptionRequests()
    await loadBusinessFunctionOptions()
  } catch (error: any) {
    ElMessage.error(error.message || '提交申请失败')
  } finally {
    bfOptionRequestSubmitting.value = false
  }
}

const searchCatalog = async (keyword: string) => {
  if (!selectedSpaceId.value) return
  catalogLoading.value = true
  try {
    const res = await toolsApi.getDataSecureFieldCatalog(
      props.toolId,
      selectedSpaceId.value,
      0,
      100,
      keyword || undefined
    )
    catalogOptions.value = res.items
  } finally {
    catalogLoading.value = false
  }
}
const loadUsageReports = async () => {
  const res = await toolsApi.getDataSecureFieldUsageReports(props.toolId, {
    project_space_id: selectedSpaceId.value || undefined,
    limit: 100
  })
  usageReports.value = res.items
}
const loadClassificationResults = async () => {
  if (!selectedSpaceId.value) return
  const res = await toolsApi.getDataSecureClassificationResults(props.toolId, selectedSpaceId.value, 0, 200)
  classificationResults.value = res.items
}

const onUsageFieldSelectionChange = () => {
  const ids = usageForm.field_entry_ids
  const set = new Set(ids)
  for (const key of Object.keys(usageExtrasState)) {
    const n = Number(key)
    if (!set.has(n)) {
      delete usageExtrasState[n]
    }
  }
  for (const id of ids) {
    if (!(id in usageExtrasState)) {
      usageExtrasState[id] = {}
    }
  }
}

const onSpaceChange = async () => {
  woPage.value = 1
  mineUrPage.value = 1
  mineFrPage.value = 1
  mineBfPage.value = 1
  mineExportSpaceId.value = selectedSpaceId.value
  focusMode.value = 'questionnaire'
  fieldUsageAlreadySubmitted.value = false
  lastAssessmentId.value = null
  lastResult.value = null
  await loadQuestions()
  await loadLifecycleUsageFields()
  await loadBusinessFunctionOptions()
  await loadWorkOrders()
  await refreshUsageUnlock()
  await loadMineUsageReports()
  await loadMineFieldRequests()
  await searchCatalog('')
  usageForm.field_entry_ids = []
  usageForm.notes = ''
  Object.keys(usageExtrasState).forEach((k) => delete usageExtrasState[Number(k)])
  await loadUsageReports()
  await loadClassificationResults()
}

const submitAssessment = async () => {
  if (!selectedSpaceId.value) {
    ElMessage.warning('请先选择项目空间')
    return
  }
  if (!form.function_name.trim()) {
    ElMessage.warning('请填写功能名称')
    return
  }
  const unanswered = questions.value.find((q) => answersMap[q.id] !== true && answersMap[q.id] !== false)
  if (unanswered) {
    ElMessage.warning(`请先完成题目「${unanswered.title}」的选择（是/否）`)
    return
  }
  const answers = questions.value.map((q) => ({
    question_id: q.id,
    answer_bool: answersMap[q.id] === true
  }))
  submitting.value = true
  try {
    const res = await toolsApi.submitDataSecureAssessment(props.toolId, {
      project_space_id: selectedSpaceId.value,
      function_name: form.function_name.trim().slice(0, 500),
      answers
    })
    lastResult.value = res
    lastAssessmentId.value = res.id
    fieldUsageAlreadySubmitted.value = false
    if (res.is_related) {
      focusMode.value = 'usage'
    } else {
      focusMode.value = 'done'
    }
    ElMessage.success('已提交相关性判定')
    await loadWorkOrders()
    await refreshUsageUnlock()
    if (!res.is_related) {
      await loadClassificationResults()
    }
  } catch (error: any) {
    ElMessage.error(error.message || '提交失败')
  } finally {
    submitting.value = false
  }
}
const submitFieldRequest = async () => {
  if (!selectedSpaceId.value) return ElMessage.warning('请先选择项目空间')
  if (!fieldRequestForm.field_name.trim()) return ElMessage.warning('请填写数据字段名称')
  requestSubmitting.value = true
  try {
    await toolsApi.createDataSecureFieldRequest(props.toolId, {
      project_space_id: selectedSpaceId.value,
      field_name: fieldRequestForm.field_name.trim()
    })
    ElMessage.success('字段新增申请已提交')
    fieldRequestForm.field_name = ''
    fieldRequestDialogVisible.value = false
    await loadMineFieldRequests()
  } catch (error: any) {
    ElMessage.error(error.message || '提交申请失败')
  } finally {
    requestSubmitting.value = false
  }
}
const submitUsageReport = async () => {
  if (!selectedSpaceId.value) return ElMessage.warning('请先选择项目空间')
  if (!usageReportingUnlocked.value) {
    ElMessage.warning('请先完成相关性判定且结果为「相关」')
    return
  }
  if (!usageForm.field_entry_ids.length) return ElMessage.warning('请至少选择一个数据字段')
  if (!lastAssessmentId.value) {
    ElMessage.warning('缺少问卷提交记录，请重新完成相关性判定')
    return
  }
  usageSubmitting.value = true
  try {
    const lines = usageForm.field_entry_ids.map((id) => ({
      catalog_entry_id: id,
      extra_fields: { ...(usageExtrasState[id] || {}) }
    }))
    await toolsApi.createDataSecureFieldUsageReport(props.toolId, {
      project_space_id: selectedSpaceId.value,
      assessment_submission_id: lastAssessmentId.value,
      lines,
      notes: usageForm.notes.trim()
    })
    usageForm.field_entry_ids = []
    usageForm.notes = ''
    Object.keys(usageExtrasState).forEach((k) => delete usageExtrasState[Number(k)])
    fieldUsageAlreadySubmitted.value = true
    focusMode.value = 'done'
    ElMessage.success('填报已提交，等待负责人审批')
    await loadUsageReports()
    await loadWorkOrders()
    await loadMineUsageReports()
    await loadClassificationResults()
  } catch (error: any) {
    ElMessage.error(error.message || '提交填报失败')
  } finally {
    usageSubmitting.value = false
  }
}

const loadAll = async () => {
  loading.value = true
  loadError.value = ''
  mineTabLoadError.value = ''
  try {
    await loadSpaces()
    await loadQuestions()
    await loadLifecycleUsageFields()
    await loadBusinessFunctionOptions()
    await loadWorkOrders()
    await loadMineUsageReports()
    await loadMineFieldRequests()
    await loadMineBfOptionRequests()
    await refreshUsageUnlock()
    await searchCatalog('')
    await loadUsageReports()
    await loadClassificationResults()
  } catch (error: any) {
    const message = error.message || '加载数据失败'
    loadError.value = message
    ElMessage.error(message)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  void loadAll()
})
</script>

<style scoped>
.data-secure-manage-panel {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.section-hint {
  color: #606266;
  font-size: 13px;
  margin: 0 0 12px;
}

.section-alert {
  margin-bottom: 12px;
}

.form-label-with-tip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

.question-help-link {
  font-size: 12px;
}

.question-help-content {
  max-height: 62vh;
  overflow: auto;
  line-height: 1.65;
}

.markdown-body :deep(table) {
  border-collapse: collapse;
  width: 100%;
}

.markdown-body :deep(th),
.markdown-body :deep(td) {
  border: 1px solid #dcdfe6;
  padding: 6px 8px;
}

.markdown-body :deep(img) {
  max-width: 100%;
  height: auto;
}

.result-alert {
  margin-top: 12px;
}

.table-pagination {
  margin-top: 12px;
  display: flex;
  justify-content: flex-end;
}

.field-request-hint {
  display: inline-block;
  margin-top: 8px;
}

.usage-submit-wrap {
  margin-top: 16px;
}

.ds-focus-toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  margin-bottom: 4px;
}

.toolbar-hint {
  font-size: 13px;
  color: #909399;
}

.done-card .new-ticket-btn {
  margin-top: 12px;
}

.export-mine-wrap {
  margin-top: 8px;
}

.locked-card :deep(.el-card__body) {
  padding-top: 8px;
}

.ds-space-bar .space-bar-hint {
  margin-top: 10px;
  margin-bottom: 0;
}

.ds-main-tabs :deep(.el-tabs__content) {
  padding-top: 12px;
}

.ds-fill-pane,
.ds-mine-pane {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.mine-toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
}

.export-filter-form {
  max-width: 560px;
  margin-bottom: 12px;
}

.panel-load-error {
  margin-top: 12px;
}

.ds-mine-inner-tabs :deep(.el-tabs__content) {
  padding-top: 8px;
}

.mine-orders-stack {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.field-request-hint--locked {
  display: inline-block;
  margin-top: 12px;
}

.field-request-dialog .dialog-hint {
  margin-top: 0;
}

.field-fn-hint {
  margin-top: 8px;
  margin-bottom: 0;
}
</style>
