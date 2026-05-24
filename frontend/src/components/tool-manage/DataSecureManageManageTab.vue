<template>
  <div class="data-secure-manage-manage-tab" v-loading="loading">
    <el-card shadow="never">
      <template #header>数据安全治理（管理）</template>
      <p class="section-hint">
        在此配置项目空间、相关性问卷与判定规则、数据字段主表与数据生命周期字段、分类分级与安全要求。用户侧按「问卷 →（相关则）字段填报」顺序使用。
      </p>
      <el-alert v-if="loadError" type="error" :closable="false" show-icon :title="loadError" />
      <template v-else>
        <el-tabs v-model="tab">
          <el-tab-pane label="项目空间" name="spaces">
            <el-form :inline="true" @submit.prevent class="inline-form">
              <el-form-item label="空间名称"><el-input v-model="spaceForm.name" placeholder="项目A" @blur="onSpaceNameBlur" /></el-form-item>
              <el-form-item label="空间标识">
                <el-input
                  v-model="spaceForm.space_key"
                  placeholder="根据名称自动生成，可修改"
                  @input="onSpaceKeyInput"
                />
              </el-form-item>
              <el-form-item label="说明"><el-input v-model="spaceForm.description" placeholder="可选" /></el-form-item>
              <el-form-item label="复制配置自">
                <el-select
                  v-model="spaceForm.copy_from_project_space_id"
                  clearable
                  filterable
                  placeholder="不复制（空白配置）"
                  style="width: 260px"
                >
                  <el-option
                    v-for="s in spaces"
                    :key="s.id"
                    :label="`${s.name}（${s.space_key}）`"
                    :value="s.id"
                  />
                </el-select>
              </el-form-item>
              <el-form-item><el-button type="primary" @click="createSpace">新增空间</el-button></el-form-item>
            </el-form>
            <p class="section-hint">
              选择「复制配置自」后，将复制该空间的问卷、相关性规则、数据生命周期表头（含内置列约束）、分类树、分类分级/安全要求绑定、关键词分类规则与显式分类矩阵；不包含主表数据字段行与填报记录。须按提示填写变更原因（至少 5 个字）。
            </p>
            <el-table :data="spaces" stripe>
              <el-table-column prop="space_key" label="空间标识" width="180" />
              <el-table-column prop="name" label="空间名称" width="180" />
              <el-table-column prop="description" label="说明" min-width="220" />
              <el-table-column label="状态" width="120">
                <template #default="scope">
                  <el-tag :type="scope.row.is_active ? 'success' : 'info'">{{ scope.row.is_active ? '启用' : '停用' }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column label="操作" width="200">
                <template #default="scope">
                  <el-button type="primary" link @click="toggleSpace(scope.row)">{{ scope.row.is_active ? '停用' : '启用' }}</el-button>
                  <el-button type="danger" link @click="confirmDeleteSpace(scope.row)">删除</el-button>
                </template>
              </el-table-column>
            </el-table>
          </el-tab-pane>

          <el-tab-pane label="功能相关性判定问卷" name="questionnaire">
            <el-form :inline="true" @submit.prevent class="inline-form">
              <el-form-item label="项目空间">
                <el-select v-model="selectedSpaceId" style="width: 220px" @change="loadQuestionnaireData">
                  <el-option v-for="space in spaces" :key="space.id" :label="space.name" :value="space.id" />
                </el-select>
              </el-form-item>
            </el-form>
            <el-tabs v-model="questionnaireInnerTab" class="ds-manage-inner-tabs">
              <el-tab-pane label="问卷题目" name="questions">
                <el-form :inline="true" @submit.prevent class="inline-form">
                  <el-form-item label="题目标题"><el-input v-model="questionForm.title" placeholder="是否涉及个人信息数据" @blur="onQuestionTitleBlur" /></el-form-item>
                  <el-form-item label="题目标识">
                    <el-input
                      v-model="questionForm.question_key"
                      placeholder="根据标题自动生成，可修改"
                      @input="onQuestionKeyInput"
                    />
                  </el-form-item>
                  <el-form-item label="问题说明（选填）">
                    <cloud-markdown-editor
                      v-model="questionForm.help_text"
                      :rows="8"
                      :maxlength="8000"
                      placeholder="支持 Markdown（长文本、图片、表格等）。使用侧点击“查看说明”链接后弹窗展示。"
                    />
                  </el-form-item>
                  <el-form-item><el-button type="primary" @click="createQuestion">新增题目</el-button></el-form-item>
                </el-form>
                <el-form label-position="top" @submit.prevent class="inline-form">
                  <el-form-item label="批量新增题目（每行仅标题，或 question_key,标题）">
                    <el-input
                      v-model="questionBatchText"
                      type="textarea"
                      :rows="4"
                      style="width: 560px"
                      placeholder="仅标题（自动生成标识）：&#10;是否涉及个人信息数据&#10;是否涉及敏感数据&#10;&#10;或显式指定：&#10;has_personal_data,是否涉及个人信息数据"
                    />
                  </el-form-item>
                  <el-form-item><el-button type="primary" plain @click="createQuestionBatch">批量新增题目</el-button></el-form-item>
                </el-form>
                <el-table :data="questionsDisplayOrdered" stripe>
                  <el-table-column prop="question_key" label="标识" width="180" />
                  <el-table-column prop="title" label="题目" min-width="220" />
                  <el-table-column label="问题说明" width="100" align="center">
                    <template #default="scope">
                      <el-tag :type="scope.row.help_text ? 'success' : 'info'" size="small">{{ scope.row.help_text ? '已配置' : '未配置' }}</el-tag>
                    </template>
                  </el-table-column>
                  <el-table-column label="顺序" width="148">
                    <template #default="scope">
                      <el-button link type="primary" :disabled="scope.$index === 0" @click="moveQuestionOrderUp(scope.row)">
                        上移
                      </el-button>
                      <el-button
                        link
                        type="primary"
                        :disabled="scope.$index === questionsDisplayOrdered.length - 1"
                        @click="moveQuestionOrderDown(scope.row)"
                      >
                        下移
                      </el-button>
                    </template>
                  </el-table-column>
                  <el-table-column label="状态" width="120">
                    <template #default="scope">
                      <el-tag :type="scope.row.is_active ? 'success' : 'info'">{{ scope.row.is_active ? '启用' : '停用' }}</el-tag>
                    </template>
                  </el-table-column>
                  <el-table-column label="操作" width="260">
                    <template #default="scope">
                      <el-button type="primary" link @click="openQuestionHelpDialog(scope.row)">编辑说明</el-button>
                      <el-button type="primary" link @click="toggleQuestion(scope.row)">{{ scope.row.is_active ? '停用' : '启用' }}</el-button>
                      <el-button type="danger" link @click="confirmDeleteQuestion(scope.row)">删除</el-button>
                    </template>
                  </el-table-column>
                </el-table>
              </el-tab-pane>
              <el-tab-pane label="相关性判定" name="relevance">
                <el-form :inline="true" @submit.prevent class="inline-form">
                  <el-form-item label="相关阈值"><el-input-number v-model="ruleForm.min_yes_count" :min="0" /></el-form-item>
                  <el-form-item label="逻辑表达式">
                    <el-input
                      v-model="ruleForm.logic_expression"
                      style="width: 420px"
                      placeholder="例如：(has_personal_data and has_privacy_data) or has_important_data"
                    />
                  </el-form-item>
                  <el-form-item label="规则说明"><el-input v-model="ruleForm.notes" style="width: 360px" /></el-form-item>
                  <el-form-item><el-button type="primary" @click="saveRule">保存规则</el-button></el-form-item>
                </el-form>
                <el-card shadow="never" class="expr-builder-card">
                  <template #header>表达式构建器</template>
                  <div class="expr-builder-row">
                    <el-button size="small" @click="appendExpressionToken('(')">(</el-button>
                    <el-button size="small" @click="appendExpressionToken(')')">)</el-button>
                    <el-button size="small" type="primary" plain @click="appendExpressionToken(' and ')">AND</el-button>
                    <el-button size="small" type="primary" plain @click="appendExpressionToken(' or ')">OR</el-button>
                    <el-button size="small" type="danger" plain @click="clearExpression">清空</el-button>
                  </div>
                  <div class="expr-builder-row question-keys-wrap">
                    <el-tag
                      v-for="q in questions.filter((item) => item.is_active)"
                      :key="q.question_key"
                      class="question-key-tag"
                      @click="appendExpressionToken(q.question_key)"
                    >
                      {{ q.question_key }}
                    </el-tag>
                  </div>
                  <el-alert
                    :type="expressionValidation.valid ? 'success' : 'warning'"
                    :closable="false"
                    show-icon
                    :title="expressionValidation.message"
                    class="expr-alert"
                  />
                  <div class="section-hint">括号检查：{{ unmatchedParenHint }}</div>
                  <p class="section-hint">点击题目标识和运算符即可拼接表达式，手动编辑也可。</p>
                </el-card>
                <p class="section-hint">
                  表达式仅支持题目标识、and / or、括号。例如：<code>(q1 and q3) or q2</code>。
                </p>
              </el-tab-pane>
            </el-tabs>
          </el-tab-pane>

          <el-tab-pane label="字段与主表" name="field-governance">
            <el-form :inline="true" @submit.prevent class="inline-form">
              <el-form-item label="项目空间">
                <el-select v-model="selectedSpaceId" style="width: 220px" @change="loadFieldGovernanceData">
                  <el-option v-for="space in spaces" :key="space.id" :label="space.name" :value="space.id" />
                </el-select>
              </el-form-item>
            </el-form>

            <el-tabs v-model="fieldGovInnerTab" class="ds-manage-inner-tabs">
              <el-tab-pane label="数据生命周期字段" name="lifecycle">
                <el-alert
                  v-if="!selectedSpaceId"
                  type="warning"
                  :closable="false"
                  show-icon
                  title="请先在上方选择项目空间，再新增自定义字段。"
                  class="section-alert"
                />
                <el-alert
                  v-else-if="!spaces.length"
                  type="info"
                  :closable="false"
                  show-icon
                  title="请先在「项目空间」页签中创建至少一个项目空间。"
                  class="section-alert"
                />
                <p class="section-hint">
                  字段 Key 须小写字母开头，仅含小写字母、数字、下划线（如 data_owner）；填写「字段名称」失焦后将按规则自动生成，也可手动改。仅工具负责人可新增/保存/删除自定义字段。
                  内置「数据字段」（field_name）与「业务功能」（business_function）与自定义列一同列出：二者<strong>不允许删除，且顺序不与自定义列换位</strong>（仍可在下表调整自定义列相对顺序）；字段限制（必填、长度、正则、允许值等）可按治理需要编辑。
                  用户填写页字段顺序与导出列顺序均与下表自上而下一致，详见表下灰色提示。
                </p>
                <el-form :inline="true" @submit.prevent class="inline-form">
                  <el-form-item label="字段名称"><el-input v-model="newLifecycleField.label" placeholder="数据Owner" @blur="onLifecycleLabelBlur" /></el-form-item>
                  <el-form-item label="字段 Key">
                    <el-input v-model="newLifecycleField.field_key" placeholder="根据名称自动生成，可修改" @input="onLifecycleFieldKeyInput" />
                  </el-form-item>
                  <el-form-item label="输入类型">
                    <el-select v-model="newLifecycleField.input_type" style="width: 180px">
                      <el-option v-for="op in fieldInputTypeOptions" :key="op.value" :label="op.label" :value="op.value" />
                    </el-select>
                  </el-form-item>
                  <el-form-item>
                    <el-button type="primary" native-type="button" :loading="lifecycleCreating" @click="createLifecycleField">新增字段</el-button>
                  </el-form-item>
                </el-form>
                <el-form label-position="top" @submit.prevent class="inline-form">
                  <el-form-item label="批量新增生命周期字段（每行：仅名称 或 field_key,名称,type）">
                    <el-input
                      v-model="lifecycleBatchText"
                      type="textarea"
                      :rows="4"
                      style="width: 680px"
                      placeholder="仅名称（自动生成 key，类型默认 text）：&#10;数据Owner&#10;保留策略,single_select&#10;&#10;或完整：&#10;data_owner,数据Owner,text"
                    />
                  </el-form-item>
                  <el-form-item><el-button type="primary" plain @click="createLifecycleFieldBatch">批量新增字段</el-button></el-form-item>
                </el-form>
                <field-config-manager-table
                  :rows="lifecycleFieldRows"
                  :loading="lifecycleLoading"
                  :saving="lifecycleSaving"
                  :input-type-options="fieldInputTypeOptions"
                  :delete-disabled-field-keys="[...lifecycleFieldDeleteProtectedKeys]"
                  :sort-reorder-locked-field-keys="[...lifecycleFieldDeleteProtectedKeys]"
                  :load-distinct-values-by-field-key="collectDistinctOptionValuesByFieldKey"
                  @save="saveLifecycleFields"
                  @refresh="loadLifecycleFieldConfigs"
                  @delete="deleteLifecycleField"
                />
              </el-tab-pane>
              <el-tab-pane label="数据字段主表" name="catalog">
                <p class="section-hint">
                  用户申请新增时仅需填写「数据字段」名称；审核通过后，工具负责人在此表点击「维护其他信息」，按数据生命周期字段配置填写各列取值。
                  工具负责人也可直接「手动新增」或通过「导入 CSV」批量写入主表，无需经过申请。
                  导入 CSV 时，除首列「数据字段」外，若表头对应尚未在「数据生命周期字段」中配置的列，系统将按列名自动新建为<strong>单行文本</strong>字段（默认不做必填、长度、选项等限制），并提示负责人到「数据生命周期字段」子页签补全限制。
                  推荐表头格式为「列显示名[field_key]」（field_key 须小写字母开头）；纯英文合法 key 也可直接作为表头。
                </p>
                <p class="section-hint">
                  口径说明：数据字段（field_name）主表中保持唯一；同一数据字段可关联多个业务功能（business_function 多选）。后续分类分级与安全要求仅针对去重后的数据字段计算，不依赖其他生命周期字段。
                </p>
                <div class="inline-form catalog-toolbar">
                  <el-button type="primary" :disabled="!selectedSpaceId" @click="openManualCatalogCreate">手动新增主表记录</el-button>
                  <el-button :disabled="!selectedSpaceId" @click="downloadCatalogCsvTemplate">下载 CSV 模板</el-button>
                  <el-button :disabled="!selectedSpaceId" @click="triggerCatalogCsvImport">导入 CSV</el-button>
                  <input
                    ref="catalogCsvInputRef"
                    type="file"
                    accept=".csv,text/csv"
                    class="catalog-csv-input"
                    @change="onCatalogCsvFileChange"
                  />
                </div>
                <el-form :inline="true" @submit.prevent class="inline-form">
                  <el-form-item label="字段检索">
                    <el-input v-model="fieldCatalogQuery" placeholder="支持字段名模糊搜索" style="width: 280px" />
                  </el-form-item>
                  <el-form-item>
                    <el-button @click="loadFieldCatalog">查询</el-button>
                  </el-form-item>
                </el-form>
                <el-table :data="fieldCatalog" stripe>
                  <el-table-column prop="field_name" label="数据字段" min-width="220" />
                  <el-table-column prop="updated_at" label="更新时间" width="180">
                    <template #default="scope">{{ formatDate(scope.row.updated_at) }}</template>
                  </el-table-column>
                  <el-table-column label="其他信息" min-width="260">
                    <template #default="scope">
                      <span>{{ Object.keys(scope.row.extra_fields || {}).length }} 项</span>
                    </template>
                  </el-table-column>
                  <el-table-column label="操作" width="140" fixed="right">
                    <template #default="scope">
                      <el-button type="primary" link @click="openCatalogExtraEdit(scope.row)">维护其他信息</el-button>
                    </template>
                  </el-table-column>
                </el-table>
              </el-tab-pane>
            </el-tabs>
          </el-tab-pane>

          <el-tab-pane label="分类分级和要求治理" name="classification-governance">
            <el-form :inline="true" @submit.prevent class="inline-form">
              <el-form-item label="项目空间">
                <el-select v-model="selectedSpaceId" style="width: 220px" @change="onStructuredSpaceChange">
                  <el-option v-for="space in spaces" :key="space.id" :label="space.name" :value="space.id" />
                </el-select>
              </el-form-item>
              <el-form-item>
                <el-button :disabled="!selectedSpaceId" @click="loadStructuredGovernanceData">刷新</el-button>
              </el-form-item>
            </el-form>
            <p class="section-hint">
              与「数据分类分级库」思路一致：<strong>数据字段主表</strong>在「字段与主表」页签；本页维护<strong>多级分类树</strong>（默认常用为根下一级、再下一级；可按需在任意节点下继续新增子级）、
              <strong>密级</strong>（C0-Public … C3-Secret）及 <strong>数据安全要求</strong>。保存密级后会同步到使用侧「分类分级结果」自动快照。
              CSV 导入为逐行调用接口，请控制单次行数；分类树 CSV 每行指定「上级节点标识」与「节点标识」，按依赖顺序导入（可先根后子，多轮直至全部成功）。
            </p>
            <el-tabs v-model="classificationInnerTab" class="ds-manage-inner-tabs">
              <el-tab-pane label="工作台" name="workbench">
                <p class="section-hint">日常维护建议按「密级绑定 → 安全要求 → 求值预览」顺序操作。</p>
                <p class="section-hint">将主表数据字段与分类路径（可选任意深度；绑定终点为最细一级分类节点）、密级（C0–C3）绑定。</p>
                <el-card shadow="never" class="workbench-batch-card">
                  <template #header>文本批量导入（与「高级配置」CSV 表头一致）</template>
                  <p class="section-hint">
                    可将 Excel 另存为 CSV 后整段粘贴（须含表头）。与高级配置中的「从文本导入」共用同一编辑区；也可在「高级配置」下载模板或上传文件。
                  </p>
                  <el-form label-position="top" class="governance-batch-text-form" @submit.prevent>
                    <el-form-item label="分类树">
                      <el-input
                        v-model="governanceTaxonomyBatchText"
                        type="textarea"
                        :rows="3"
                        placeholder="粘贴完整 CSV（含表头），与高级配置一致"
                      />
                      <el-button type="primary" plain :disabled="!selectedSpaceId || !governanceTaxonomyBatchText.trim()" @click="applyGovernanceTaxonomyBatchText">
                        从文本导入分类树
                      </el-button>
                    </el-form-item>
                    <el-form-item label="密级绑定">
                      <el-input
                        v-model="governanceClassGradeBatchText"
                        type="textarea"
                        :rows="3"
                        placeholder="粘贴完整 CSV（含表头）"
                      />
                      <el-button type="primary" plain :disabled="!selectedSpaceId || !governanceClassGradeBatchText.trim()" @click="applyGovernanceClassGradeBatchText">
                        从文本导入密级绑定
                      </el-button>
                    </el-form-item>
                    <el-form-item label="安全要求">
                      <el-input
                        v-model="governanceSecurityBatchText"
                        type="textarea"
                        :rows="3"
                        placeholder="粘贴完整 CSV（含表头）"
                      />
                      <el-button type="primary" plain :disabled="!selectedSpaceId || !governanceSecurityBatchText.trim()" @click="applyGovernanceSecurityBatchText">
                        从文本导入安全要求
                      </el-button>
                    </el-form-item>
                  </el-form>
                </el-card>
              <el-form :inline="true" @submit.prevent class="inline-form">
                <el-form-item label="数据字段">
                  <el-select v-model="gradeForm.catalog_entry_id" filterable placeholder="主表行" style="width: 260px">
                    <el-option v-for="e in fieldCatalog" :key="e.id" :label="e.field_name" :value="e.id" />
                  </el-select>
                </el-form-item>
                <el-form-item label="分类路径">
                  <el-cascader
                    v-model="gradeTaxonomyPath"
                    :options="taxonomyTreeForGradeCascader"
                    :props="gradeTaxonomyCascaderProps"
                    clearable
                    filterable
                    placeholder="选择根→…→最细分类；可只选根或中间层（与密级绑定的分类粒度一致）"
                    style="width: 420px"
                  />
                </el-form-item>
                <el-form-item label="密级">
                  <el-select v-model="gradeForm.confidentiality_grade" style="width: 180px">
                    <el-option v-for="g in confidentialityGrades" :key="g" :label="g" :value="g" />
                  </el-select>
                </el-form-item>
                <el-form-item label="备注"><el-input v-model="gradeForm.notes" placeholder="可选" style="width: 160px" /></el-form-item>
                <el-form-item><el-button type="primary" :disabled="!selectedSpaceId" @click="submitStructuredGrade">保存绑定</el-button></el-form-item>
              </el-form>
              <el-table :data="structuredClassGrades" stripe max-height="260">
                <el-table-column prop="field_name" label="数据字段" min-width="160" />
                <el-table-column label="分类路径" min-width="200">
                  <template #default="scope">
                    {{ scope.row.taxonomy_path || legacyTaxonomyPathLabel(scope.row) }}
                  </template>
                </el-table-column>
                <el-table-column prop="confidentiality_grade" label="密级" width="140" />
                <el-table-column prop="notes" label="备注" min-width="120" show-overflow-tooltip />
                <el-table-column label="操作" width="100">
                  <template #default="scope">
                    <el-button type="danger" link @click="deleteStructuredGrade(scope.row)">删除</el-button>
                  </template>
                </el-table-column>
              </el-table>

                <el-divider />
                <el-form :inline="true" @submit.prevent class="inline-form">
                <el-form-item label="数据字段">
                  <el-select v-model="secCreateForm.catalog_entry_id" filterable placeholder="主表行" style="width: 240px">
                    <el-option v-for="e in fieldCatalog" :key="e.id" :label="e.field_name" :value="e.id" />
                  </el-select>
                </el-form-item>
                <el-form-item label="优先级"><el-input-number v-model="secCreateForm.priority" :min="0" :max="1000000" /></el-form-item>
              </el-form>
                <el-form label-position="top" class="inline-form">
                <el-form-item label="要求正文">
                  <el-input v-model="secCreateForm.requirement_text" type="textarea" :rows="2" placeholder="面向读者的安全要求描述" />
                </el-form-item>
              </el-form>
                <p class="section-hint">先配置谓词（与下方表达式中的标识一致），再用构建器拼接 <code>and</code> / <code>or</code> 与括号。</p>
                <predicate-expression-editor
                v-model:rows="secPredRows"
                v-model:expression="secCreateForm.logic_expression"
                :kind-options="securityPredicateKindOptions"
                :default-row="{ token: '', kind: 'grade_equals', value: 'C1-Internal', field_key: '' }"
              >
                <template #valueEditor="{ row }">
                  <el-select v-if="row.kind === 'grade_equals'" v-model="row.value" style="width: 100%">
                    <el-option v-for="g in confidentialityGrades" :key="g" :label="g" :value="g" />
                  </el-select>
                  <el-select
                    v-else-if="
                      row.kind === 'l1_node_key' || row.kind === 'l2_node_key' || row.kind === 'taxonomy_path_node_key'
                    "
                    v-model="row.value"
                    filterable
                    remote
                    allow-create
                    default-first-option
                    clearable
                    style="width: 100%"
                    :placeholder="
                      row.kind === 'l1_node_key'
                        ? '根分类 node_key（可检索）'
                        : row.kind === 'l2_node_key'
                          ? '最细绑定分类 node_key（可检索）'
                          : '路径上任一层 node_key（可检索）'
                    "
                    :remote-method="makeTaxonomyNodeKeyRemoteMethod(row)"
                    @visible-change="handleTaxonomyNodeKeyDropdownVisible(row, $event)"
                  >
                    <el-option
                      v-for="op in taxonomyNodeKeyOptionsForRow(row)"
                      :key="op"
                      :label="op"
                      :value="op"
                    />
                  </el-select>
                  <div v-else class="inline-form" style="margin-bottom: 0; display: flex; gap: 8px; flex-wrap: wrap">
                    <el-select
                      v-model="row.field_key"
                      filterable
                      remote
                      allow-create
                      default-first-option
                      clearable
                      placeholder="生命周期字段 key"
                      style="width: 200px"
                      :remote-method="makeLifecycleFieldKeyRemoteMethod(row)"
                      @visible-change="handleLifecycleFieldKeyDropdownVisible(row, $event)"
                    >
                      <el-option
                        v-for="op in lifecycleFieldKeyOptionsForRow(row)"
                        :key="op"
                        :label="lifecycleFieldKeyLabel(op)"
                        :value="op"
                      />
                    </el-select>
                    <el-select
                      v-model="row.value"
                      filterable
                      remote
                      allow-create
                      default-first-option
                      clearable
                      :loading="lifecycleFieldValueRemoteLoading"
                      placeholder="比较值（模糊搜索）"
                      style="width: 220px"
                      :remote-method="makeLifecycleValueRemoteMethod(row)"
                      @visible-change="handleLifecycleValueDropdownVisible(row, $event)"
                    >
                      <el-option
                        v-for="op in lifecycleFieldValueRemoteOptionsForRow(row)"
                        :key="op"
                        :label="op"
                        :value="op"
                      />
                    </el-select>
                  </div>
                </template>
                </predicate-expression-editor>
                <el-button type="primary" :disabled="!selectedSpaceId" @click="submitStructuredSecurityCreate">新增安全要求</el-button>
                <el-table :data="securityRequirementsOrdered" stripe max-height="240">
                <el-table-column prop="field_name" label="数据字段" width="140" />
                <el-table-column prop="priority" label="优先级" width="80" />
                <el-table-column prop="logic_expression" label="表达式" min-width="140" show-overflow-tooltip />
                <el-table-column label="谓词" min-width="160" show-overflow-tooltip>
                  <template #default="scope">{{ JSON.stringify(scope.row.predicate_map || {}) }}</template>
                </el-table-column>
                <el-table-column label="状态" width="80">
                  <template #default="scope">
                    <el-tag :type="scope.row.is_active ? 'success' : 'info'">{{ scope.row.is_active ? '启用' : '停' }}</el-tag>
                  </template>
                </el-table-column>
                  <el-table-column label="顺序" width="148">
                    <template #default="scope">
                      <el-button
                        link
                        type="primary"
                        :disabled="isSecurityRequirementMoveUpDisabled(scope.row)"
                        @click="moveSecurityRequirementUp(scope.row)"
                      >
                        上移
                      </el-button>
                      <el-button
                        link
                        type="primary"
                        :disabled="isSecurityRequirementMoveDownDisabled(scope.row)"
                        @click="moveSecurityRequirementDown(scope.row)"
                      >
                        下移
                      </el-button>
                    </template>
                  </el-table-column>
                <el-table-column label="操作" width="150">
                  <template #default="scope">
                    <el-button type="primary" link @click="toggleStructuredSecurityReq(scope.row)">
                      {{ scope.row.is_active ? '停用' : '启用' }}
                    </el-button>
                    <el-button type="danger" link @click="deleteStructuredSecurityReq(scope.row)">删除</el-button>
                  </template>
                </el-table-column>
                </el-table>

                <el-divider />
                <p class="section-hint">关键词分类分级规则：命中后用于自动分类分级计算，可按需启停或删除。</p>
                <el-form :inline="true" @submit.prevent class="inline-form">
                  <el-form-item label="规则检索">
                    <el-input v-model="structuredRuleKeyword" clearable placeholder="关键词 / 分类 / 分级" style="width: 260px" />
                  </el-form-item>
                </el-form>
                <el-table :data="filteredStructuredClassificationRules" stripe max-height="220">
                  <el-table-column prop="keyword" label="关键词" min-width="140" />
                  <el-table-column prop="category" label="分类" width="130" />
                  <el-table-column prop="level" label="分级" width="130" />
                  <el-table-column prop="priority" label="优先级" width="90" />
                  <el-table-column label="状态" width="80">
                    <template #default="scope">
                      <el-tag :type="scope.row.is_active ? 'success' : 'info'">{{ scope.row.is_active ? '启用' : '停用' }}</el-tag>
                    </template>
                  </el-table-column>
                  <el-table-column label="顺序" width="148">
                    <template #default="scope">
                      <el-button
                        link
                        type="primary"
                        :disabled="isClassificationRuleMoveUpDisabled(scope.row)"
                        @click="moveClassificationRuleUp(scope.row)"
                      >
                        上移
                      </el-button>
                      <el-button
                        link
                        type="primary"
                        :disabled="isClassificationRuleMoveDownDisabled(scope.row)"
                        @click="moveClassificationRuleDown(scope.row)"
                      >
                        下移
                      </el-button>
                    </template>
                  </el-table-column>
                  <el-table-column label="操作" width="150">
                    <template #default="scope">
                      <el-button type="primary" link @click="toggleStructuredClassificationRule(scope.row)">
                        {{ scope.row.is_active ? '停用' : '启用' }}
                      </el-button>
                      <el-button type="danger" link @click="deleteStructuredClassificationRule(scope.row)">删除</el-button>
                    </template>
                  </el-table-column>
                </el-table>

                <el-divider />
                <p class="section-hint">显式分类矩阵：按字段名/扩展匹配优先命中，可按需启停或删除。</p>
                <el-form :inline="true" @submit.prevent class="inline-form">
                  <el-form-item label="矩阵检索">
                    <el-input v-model="structuredMatrixKeyword" clearable placeholder="字段名 / 分类 / 分级" style="width: 260px" />
                  </el-form-item>
                </el-form>
                <el-table :data="filteredStructuredClassificationMatrix" stripe max-height="220">
                  <el-table-column prop="field_name" label="字段名" min-width="140" />
                  <el-table-column prop="category" label="分类" width="130" />
                  <el-table-column prop="level" label="分级" width="130" />
                  <el-table-column prop="priority" label="优先级" width="90" />
                  <el-table-column label="状态" width="80">
                    <template #default="scope">
                      <el-tag :type="scope.row.is_active ? 'success' : 'info'">{{ scope.row.is_active ? '启用' : '停用' }}</el-tag>
                    </template>
                  </el-table-column>
                  <el-table-column label="顺序" width="148">
                    <template #default="scope">
                      <el-button
                        link
                        type="primary"
                        :disabled="isClassificationMatrixMoveUpDisabled(scope.row)"
                        @click="moveClassificationMatrixUp(scope.row)"
                      >
                        上移
                      </el-button>
                      <el-button
                        link
                        type="primary"
                        :disabled="isClassificationMatrixMoveDownDisabled(scope.row)"
                        @click="moveClassificationMatrixDown(scope.row)"
                      >
                        下移
                      </el-button>
                    </template>
                  </el-table-column>
                  <el-table-column label="操作" width="150">
                    <template #default="scope">
                      <el-button type="primary" link @click="toggleStructuredClassificationMatrix(scope.row)">
                        {{ scope.row.is_active ? '停用' : '启用' }}
                      </el-button>
                      <el-button type="danger" link @click="deleteStructuredClassificationMatrix(scope.row)">删除</el-button>
                    </template>
                  </el-table-column>
                </el-table>

                <el-divider />
                <p class="section-hint">根据当前密级与各条安全要求配置，预览指定主表字段的命中情况。</p>
                <el-form :inline="true" @submit.prevent class="inline-form">
                <el-form-item label="数据字段">
                  <el-select v-model="structuredEvalCatalogId" filterable placeholder="选择主表行" style="width: 260px">
                    <el-option v-for="e in fieldCatalog" :key="e.id" :label="e.field_name" :value="e.id" />
                  </el-select>
                </el-form-item>
                <el-form-item><el-button :disabled="!selectedSpaceId || !structuredEvalCatalogId" @click="runStructuredEval">求值</el-button></el-form-item>
                </el-form>
                <template v-if="structuredEvalResult">
                <p class="section-hint">
                  展示路径：<strong>{{ structuredEvalResult.category_path }}</strong>；当前密级：<strong>{{ structuredEvalResult.confidentiality_grade || '（未绑定）' }}</strong>
                </p>
                  <el-table :data="structuredEvalResult.hits" stripe>
                  <el-table-column prop="requirement_id" label="要求ID" width="90" />
                  <el-table-column prop="matched" label="命中" width="70">
                    <template #default="scope">
                      <el-tag :type="scope.row.matched ? 'success' : 'info'">{{ scope.row.matched ? '是' : '否' }}</el-tag>
                    </template>
                  </el-table-column>
                  <el-table-column prop="logic_expression" label="表达式" min-width="140" show-overflow-tooltip />
                  <el-table-column prop="requirement_text" label="要求摘要" min-width="200" show-overflow-tooltip />
                  </el-table>
                </template>
              </el-tab-pane>
              <el-tab-pane label="高级配置" name="advanced">
                <div class="inline-form catalog-toolbar governance-csv-toolbar">
                  <span class="toolbar-label">分类树 CSV：</span>
                  <el-button :disabled="!selectedSpaceId" @click="downloadGovernanceTaxonomyTemplate">下载模板</el-button>
                  <el-button :disabled="!selectedSpaceId" @click="triggerGovernanceTaxonomyCsv">导入 CSV</el-button>
                  <input ref="governanceTaxonomyCsvInputRef" type="file" accept=".csv,text/csv" class="catalog-csv-input" @change="onGovernanceTaxonomyCsvChange" />
                </div>
                <el-form label-position="top" class="governance-batch-text-form" @submit.prevent>
                  <el-form-item label="分类树（文本批量：粘贴完整 CSV，含表头，与文件导入一致）">
                    <el-input
                      v-model="governanceTaxonomyBatchText"
                      type="textarea"
                      :rows="4"
                      placeholder="首行表头须含「节点名称」「节点标识」等，与下载模板一致"
                    />
                    <el-button type="primary" plain :disabled="!selectedSpaceId || !governanceTaxonomyBatchText.trim()" @click="applyGovernanceTaxonomyBatchText">
                      从文本导入分类树
                    </el-button>
                  </el-form-item>
                </el-form>
                <div class="inline-form catalog-toolbar governance-csv-toolbar">
                  <span class="toolbar-label">密级绑定 CSV：</span>
                  <el-button :disabled="!selectedSpaceId" @click="downloadGovernanceClassGradeTemplate">下载模板</el-button>
                  <el-button :disabled="!selectedSpaceId" @click="triggerGovernanceClassGradeCsv">导入 CSV</el-button>
                  <input ref="governanceClassGradeCsvInputRef" type="file" accept=".csv,text/csv" class="catalog-csv-input" @change="onGovernanceClassGradeCsvChange" />
                </div>
                <el-form label-position="top" class="governance-batch-text-form" @submit.prevent>
                  <el-form-item label="密级绑定（文本批量：粘贴完整 CSV，含表头）">
                    <el-input
                      v-model="governanceClassGradeBatchText"
                      type="textarea"
                      :rows="4"
                      placeholder="首行表头须含「数据字段」「密级」等，与下载模板一致"
                    />
                    <el-button type="primary" plain :disabled="!selectedSpaceId || !governanceClassGradeBatchText.trim()" @click="applyGovernanceClassGradeBatchText">
                      从文本导入密级绑定
                    </el-button>
                  </el-form-item>
                </el-form>
                <div class="inline-form catalog-toolbar governance-csv-toolbar">
                  <span class="toolbar-label">安全要求 CSV：</span>
                  <el-button :disabled="!selectedSpaceId" @click="downloadGovernanceSecurityTemplate">下载模板</el-button>
                  <el-button :disabled="!selectedSpaceId" @click="triggerGovernanceSecurityCsv">导入 CSV</el-button>
                  <input ref="governanceSecurityCsvInputRef" type="file" accept=".csv,text/csv" class="catalog-csv-input" @change="onGovernanceSecurityCsvChange" />
                </div>
                <el-form label-position="top" class="governance-batch-text-form" @submit.prevent>
                  <el-form-item label="安全要求（文本批量：粘贴完整 CSV，含表头）">
                    <el-input
                      v-model="governanceSecurityBatchText"
                      type="textarea"
                      :rows="4"
                      placeholder="首行表头须含「数据字段」「要求摘要」「逻辑表达式」「谓词JSON」等，与下载模板一致"
                    />
                    <el-button type="primary" plain :disabled="!selectedSpaceId || !governanceSecurityBatchText.trim()" @click="applyGovernanceSecurityBatchText">
                      从文本导入安全要求
                    </el-button>
                  </el-form-item>
                </el-form>
                <div class="inline-form catalog-toolbar governance-csv-toolbar">
                  <span class="toolbar-label">配置迁移：</span>
                  <el-button :disabled="!selectedSpaceId" @click="exportConfigBundle">导出配置JSON</el-button>
                  <el-button :disabled="!selectedSpaceId" @click="triggerConfigJsonImport">导入配置JSON</el-button>
                  <input ref="configJsonInputRef" type="file" accept=".json,application/json,text/json" class="catalog-csv-input" @change="onConfigJsonFileChange" />
                </div>
                <div class="inline-form catalog-toolbar governance-csv-toolbar">
                  <span class="toolbar-label">批量删除配置：</span>
                  <el-input
                    v-model="batchDeleteJsonText"
                    type="textarea"
                    :rows="3"
                    style="width: 560px"
                    placeholder='填写 JSON 数组，如：[{"domain":"field_class_grade","target_id":"12"}]'
                  />
                  <el-button type="danger" :disabled="!selectedSpaceId || !batchDeleteJsonText.trim()" @click="submitBatchDeleteConfigs">批量删除</el-button>
                </div>
                <p class="section-hint">维护多级分类节点：填写「名称」失焦后将按规则自动生成「节点标识」，也可手动改。父节点可选任意已有节点，不选则为根级。</p>
                <el-form :inline="true" @submit.prevent class="inline-form">
                  <el-form-item label="父节点（空=根级）">
                    <el-select v-model="taxCreateForm.parent_id" clearable placeholder="不选则为根级" filterable style="width: 320px">
                      <el-option v-for="opt in taxonomyFlatParentOptions" :key="opt.id" :label="opt.label" :value="opt.id" />
                    </el-select>
                  </el-form-item>
                  <el-form-item label="名称"><el-input v-model="taxCreateForm.name" placeholder="展示名" style="width: 160px" @blur="onTaxonomyNameBlur" /></el-form-item>
                  <el-form-item label="节点标识">
                    <el-input v-model="taxCreateForm.node_key" placeholder="根据名称自动生成，可修改" style="width: 160px" @input="onTaxonomyNodeKeyInput" />
                  </el-form-item>
                  <el-form-item><el-button type="primary" :disabled="!selectedSpaceId" @click="submitTaxonomyCreate">新增节点</el-button></el-form-item>
                </el-form>
                <el-table :data="taxonomyNodesAll" stripe max-height="280">
                  <el-table-column prop="id" label="ID" width="70" />
                  <el-table-column prop="parent_id" label="父ID" width="80" />
                  <el-table-column prop="name" label="名称" min-width="140" />
                  <el-table-column prop="node_key" label="节点标识" width="140" />
                  <el-table-column label="顺序" width="148">
                    <template #default="scope">
                      <el-button
                        link
                        type="primary"
                        :disabled="isTaxonomyNodeMoveUpDisabled(scope.row)"
                        @click="moveTaxonomyNodeUp(scope.row)"
                      >
                        上移
                      </el-button>
                      <el-button
                        link
                        type="primary"
                        :disabled="isTaxonomyNodeMoveDownDisabled(scope.row)"
                        @click="moveTaxonomyNodeDown(scope.row)"
                      >
                        下移
                      </el-button>
                    </template>
                  </el-table-column>
                  <el-table-column label="状态" width="90">
                    <template #default="scope">
                      <el-tag :type="scope.row.is_active ? 'success' : 'info'">{{ scope.row.is_active ? '启用' : '停用' }}</el-tag>
                    </template>
                  </el-table-column>
                  <el-table-column label="操作" width="160">
                    <template #default="scope">
                      <el-button
                        type="warning"
                        link
                        :disabled="!scope.row.is_active"
                        @click="deactivateTaxonomyNode(scope.row)"
                      >停用</el-button>
                      <el-button type="danger" link @click="confirmDeleteTaxonomyNode(scope.row)">删除</el-button>
                    </template>
                  </el-table-column>
                </el-table>
              </el-tab-pane>
            </el-tabs>
          </el-tab-pane>

          <el-tab-pane label="变更履历" name="change-logs">
            <el-form :inline="true" @submit.prevent class="inline-form">
              <el-form-item label="项目空间">
                <el-select v-model="selectedSpaceId" style="width: 220px" @change="loadGovernanceChangeLogs">
                  <el-option v-for="space in spaces" :key="space.id" :label="space.name" :value="space.id" />
                </el-select>
              </el-form-item>
              <el-form-item label="变更域">
                <el-select v-model="changeLogDomain" clearable style="width: 220px" @change="onChangeLogDomainChange">
                  <el-option label="全部" value="" />
                  <el-option label="相关性规则" value="relevance_rule" />
                  <el-option label="填报字段配置" value="lifecycle_fields" />
                  <el-option label="分类树" value="taxonomy" />
                  <el-option label="密级绑定" value="field_class_grade" />
                  <el-option label="安全要求" value="security_requirement" />
                </el-select>
              </el-form-item>
              <el-form-item><el-button @click="loadGovernanceChangeLogs">查询</el-button></el-form-item>
            </el-form>
            <el-table :data="governanceChangeLogs" stripe>
              <el-table-column prop="created_at" label="变更时间" width="180">
                <template #default="scope">{{ formatDate(scope.row.created_at) }}</template>
              </el-table-column>
              <el-table-column prop="changed_by_name" label="变更人" width="120" />
              <el-table-column prop="domain" label="变更域" width="160" />
              <el-table-column prop="action" label="动作" width="100" />
              <el-table-column prop="target_id" label="目标" min-width="140" />
              <el-table-column prop="change_reason" label="变更原因" min-width="260" show-overflow-tooltip />
            </el-table>
            <div class="table-pagination">
              <el-pagination
                v-model:current-page="changeLogPage"
                v-model:page-size="changeLogPageSize"
                :total="changeLogTotal"
                :page-sizes="[10, 20, 50]"
                layout="total, sizes, prev, pager, next"
                @current-change="loadGovernanceChangeLogs"
                @size-change="onChangeLogPageSizeChange"
              />
            </div>
          </el-tab-pane>

          <el-tab-pane label="填报与审批中心" name="records">
            <el-form :inline="true" @submit.prevent class="inline-form">
              <el-form-item label="项目空间">
                <el-select v-model="recordSpaceId" clearable style="width: 220px" @change="onRecordSpaceFilterChange">
                  <el-option v-for="space in spaces" :key="space.id" :label="space.name" :value="space.id" />
                </el-select>
              </el-form-item>
              <el-form-item>
                <el-button @click="loadRecordsPaneData">刷新</el-button>
              </el-form-item>
            </el-form>
            <el-tabs v-model="recordsInnerTab" class="ds-manage-inner-tabs">
              <el-tab-pane label="用户填报记录" name="submissions">
              <el-table :data="assessments" stripe>
                <el-table-column prop="submitted_at" label="问卷提交时间" width="180">
                  <template #default="scope">{{ formatDate(scope.row.submitted_at) }}</template>
                </el-table-column>
                <el-table-column prop="submitted_by_name" label="提交人" width="120" />
                <el-table-column prop="function_name" label="功能名称" min-width="180" />
                <el-table-column label="问卷结果" width="120">
                  <template #default="scope">
                    <el-tag :type="scope.row.is_related ? 'warning' : 'success'">{{ scope.row.is_related ? '相关' : '不相关' }}</el-tag>
                  </template>
                </el-table-column>
              </el-table>
              <div class="table-pagination">
                <el-pagination
                  v-model:current-page="page"
                  v-model:page-size="pageSize"
                  :total="total"
                  :page-sizes="[10, 20, 50]"
                  layout="total, sizes, prev, pager, next"
                  @current-change="loadAssessmentRows"
                  @size-change="onPageSizeChange"
                />
              </div>
              <div class="inline-form">
                <el-button type="primary" plain @click="exportUsageReports">导出生命周期字段填报记录(CSV)</el-button>
              </div>
              <el-table :data="usageReports" stripe>
                <el-table-column prop="submitted_at" label="生命周期填报时间" width="180">
                  <template #default="scope">{{ formatDate(scope.row.submitted_at) }}</template>
                </el-table-column>
                <el-table-column prop="submitted_by_name" label="提交人" width="120" />
                <el-table-column prop="function_name" label="功能名称" min-width="180" />
                <el-table-column prop="review_status" label="审批状态" width="120" />
                <el-table-column label="涉及字段" min-width="260">
                  <template #default="scope">{{ (scope.row.field_names || []).join('，') }}</template>
                </el-table-column>
              </el-table>
              </el-tab-pane>
              <el-tab-pane label="待审批事项" name="approvals">
              <p class="section-hint">集中处理所有待审批内容：生命周期字段填报工单、数据字段新增申请、业务功能选项申请。</p>
              <el-tabs v-model="approvalsInnerTab" class="ds-manage-inner-tabs">
                <el-tab-pane label="生命周期填报工单" name="usage-pending">
                  <el-table :data="pendingUsageReports" stripe empty-text="暂无待审批生命周期填报工单">
                    <el-table-column prop="submitted_at" label="填报时间" width="180">
                      <template #default="scope">{{ formatDate(scope.row.submitted_at) }}</template>
                    </el-table-column>
                    <el-table-column prop="submitted_by_name" label="提交人" width="120" />
                    <el-table-column prop="function_name" label="摘要" min-width="160" />
                    <el-table-column label="涉及字段" min-width="200">
                      <template #default="scope">{{ (scope.row.field_names || []).join('，') }}</template>
                    </el-table-column>
                    <el-table-column label="操作" width="200" fixed="right">
                      <template #default="scope">
                        <el-button type="primary" link @click="reviewUsageReportRow(scope.row, 'approved')">通过</el-button>
                        <el-button type="danger" link @click="reviewUsageReportRow(scope.row, 'rejected')">驳回</el-button>
                      </template>
                    </el-table-column>
                  </el-table>
                </el-tab-pane>
                <el-tab-pane label="数据字段申请" name="field-pending">
                  <el-table :data="pendingFieldRequests" stripe empty-text="暂无待审批数据字段申请">
                    <el-table-column prop="created_at" label="申请时间" width="180">
                      <template #default="scope">{{ formatDate(scope.row.created_at) }}</template>
                    </el-table-column>
                    <el-table-column prop="requested_by_name" label="申请人" width="120" />
                    <el-table-column label="申请类型" width="160">
                      <template #default="scope">
                        {{ scope.row.request_type === 'business_function' ? '业务功能字段申请' : '数据字段字段申请' }}
                      </template>
                    </el-table-column>
                    <el-table-column prop="field_name" label="字段名称" min-width="180" />
                    <el-table-column prop="reason" label="申请说明" min-width="180" />
                    <el-table-column label="操作" width="220">
                      <template #default="scope">
                        <el-button type="success" link @click="reviewFieldRequest(scope.row.id, 'approved')">通过</el-button>
                        <el-button type="danger" link @click="reviewFieldRequest(scope.row.id, 'rejected')">驳回</el-button>
                      </template>
                    </el-table-column>
                  </el-table>
                </el-tab-pane>
                <el-tab-pane label="业务功能选项申请" name="bf-pending">
                  <el-table :data="pendingBfOptionRequests" stripe empty-text="暂无待审批业务功能选项申请">
                    <el-table-column prop="created_at" label="申请时间" width="180">
                      <template #default="scope">{{ formatDate(scope.row.created_at) }}</template>
                    </el-table-column>
                    <el-table-column prop="requested_by_name" label="申请人" width="120" />
                    <el-table-column prop="proposed_option" label="申请选项" min-width="160" />
                    <el-table-column prop="reason" label="说明" min-width="160" show-overflow-tooltip />
                    <el-table-column label="操作" width="220">
                      <template #default="scope">
                        <el-button type="success" link @click="reviewBfOptionRequest(scope.row.id, 'approved')">通过</el-button>
                        <el-button type="danger" link @click="reviewBfOptionRequest(scope.row.id, 'rejected')">驳回</el-button>
                      </template>
                    </el-table-column>
                  </el-table>
                </el-tab-pane>
              </el-tabs>
              </el-tab-pane>
              <el-tab-pane label="过审大表导出" name="export">
              <p class="section-hint">
                请选择<strong>导出目标项目空间</strong>（可与当前筛选不同）。导出该空间内<strong>审批通过</strong>的全部字段填报合并行（含分类分级与安全要求配置摘要）。筛选可多选列 key 与多个「值包含」关键词：列之间为 OR；关键词之间为 OR；未选关键词时仅要求所选列在快照中存在。
              </p>
              <el-form :inline="true" @submit.prevent class="inline-form">
                <el-form-item label="导出项目空间">
                  <el-select
                    v-model="exportConsolidatedSpaceId"
                    filterable
                    placeholder="请选择项目空间"
                    style="width: 260px"
                  >
                    <el-option
                      v-for="space in spaces.filter((s) => s.is_active)"
                      :key="space.id"
                      :label="space.name"
                      :value="space.id"
                    />
                  </el-select>
                </el-form-item>
                <el-form-item label="筛选列 key">
                  <el-select
                    v-model="consolidateFilterKeys"
                    multiple
                    filterable
                    clearable
                    allow-create
                    default-first-option
                    collapse-tags
                    collapse-tags-tooltip
                    placeholder="可多选；任一列参与匹配"
                    style="width: 320px"
                  >
                    <el-option
                      v-for="op in consolidatedExportFieldKeyOptions"
                      :key="op.value"
                      :label="op.label"
                      :value="op.value"
                    />
                  </el-select>
                </el-form-item>
                <el-form-item label="值包含">
                  <el-select
                    v-model="consolidateFilterVals"
                    multiple
                    filterable
                    clearable
                    allow-create
                    default-first-option
                    collapse-tags
                    collapse-tags-tooltip
                    placeholder="可多选关键词（OR）；不选则仅按列存在性筛选"
                    style="width: 280px"
                  />
                </el-form-item>
                <el-form-item>
                  <el-button type="primary" :disabled="!exportConsolidatedSpaceId" :loading="exportConsolidatedLoading" @click="exportConsolidatedMaster">
                    导出 CSV
                  </el-button>
                </el-form-item>
              </el-form>
              </el-tab-pane>
            </el-tabs>
          </el-tab-pane>
        </el-tabs>
      </template>
    </el-card>

    <el-dialog
      v-model="manualCatalogDialogVisible"
      title="手动新增数据字段主表"
      width="560px"
      destroy-on-close
      @closed="onManualCatalogDialogClosed"
    >
      <p class="section-hint">
        在上方已选项目空间下新增一条主表记录。其他信息可暂不填写，保存后可用「维护其他信息」补全；若已填写则按数据生命周期字段配置校验。
      </p>
      <el-form label-position="top" @submit.prevent>
        <el-form-item label="数据字段名称" required>
          <el-input v-model="manualCatalogFieldName" maxlength="200" placeholder="建议与代码或库表字段名一致" />
        </el-form-item>
      </el-form>
      <dynamic-field-inputs v-model="manualCatalogExtraFields" :fields="lifecycleDynamicFieldsForCatalogEdit" />
      <template #footer>
        <el-button @click="manualCatalogDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="manualCatalogSaving" @click="submitManualCatalogCreate">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="questionHelpDialogVisible"
      title="问题说明（填报用户点击查看）"
      width="980px"
      destroy-on-close
      @closed="onQuestionHelpDialogClosed"
    >
      <el-form v-if="questionHelpEdit" label-position="top" @submit.prevent>
        <el-form-item :label="`题目：${questionHelpEdit.title}`">
          <cloud-markdown-editor
            v-model="questionHelpEdit.help_text"
            :rows="16"
            :maxlength="8000"
            placeholder="支持 Markdown（例如：# 标题、![图片](URL)、|表头|表头|）。保存后在使用页通过“查看说明”链接弹窗展示。"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="questionHelpDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="questionHelpSaving" :disabled="!questionHelpEdit" @click="saveQuestionHelp">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="catalogExtraDialogVisible"
      title="维护数据字段其他信息"
      width="560px"
      destroy-on-close
      @closed="onCatalogExtraDialogClosed"
    >
      <template v-if="catalogExtraEditEntry">
        <p class="section-hint">
          数据字段：<strong>{{ catalogExtraEditEntry.field_name }}</strong>。以下表单项与「数据生命周期字段配置」一致（含内置「业务功能」及您新增的自定义列）；保存时将按配置校验必填与格式。
        </p>
        <el-alert
          v-if="!lifecycleDynamicFieldsForCatalogEdit.length"
          type="warning"
          :closable="false"
          show-icon
          title="当前无可编辑的其他信息列（至少应有内置「业务功能」）。若列表异常请刷新「数据生命周期字段配置」。"
          class="section-alert"
        />
        <dynamic-field-inputs v-model="catalogExtraForm" :fields="lifecycleDynamicFieldsForCatalogEdit" />
      </template>
      <template #footer>
        <el-button @click="catalogExtraDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="catalogExtraSaving" :disabled="!catalogExtraEditEntry" @click="saveCatalogExtraFields">
          保存
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { toolsApi } from '@/api/tools'
import { formatDateTime as formatDate } from '@/utils/datetime'
import { downloadApprovedConsolidatedCsv, downloadFieldUsageExportCsv } from '@/utils/csvExport'
import type {
  DataSecureAssessmentSubmission,
  DataSecureClassificationMatrix,
  DataSecureClassificationRule,
  DataSecureIdentifierKeyTarget,
  DataSecureConfigDeleteDomain,
  DataSecureConfigExportPayload,
  DataSecureConfigExportSelection,
  DataSecureFieldCatalogEntry,
  DataSecureFieldRequest,
  DataSecureBusinessFunctionOptionRequest,
  DataSecureFieldUsageReport,
  DataSecureFieldClassGrade,
  DataSecureFieldSecurityRequirement,
  DataSecureFieldSecurityRequirementEvalResponse,
  DataSecureGovernanceChangeLog,
  DataSecureProjectSpace,
  DataSecureQuestion,
  DataSecureTaxonomyNode,
  FormFieldConfigItem,
  FormFieldInputType
} from '@/api/types'
import FieldConfigManagerTable, { type FieldConfigTableRow } from '@/components/form-config/FieldConfigManagerTable.vue'
import DynamicFieldInputs from '@/components/form-config/DynamicFieldInputs.vue'
import PredicateExpressionEditor from '@/components/form-config/PredicateExpressionEditor.vue'
import CloudMarkdownEditor from '@/components/form-config/CloudMarkdownEditor.vue'

const props = defineProps<{ toolId: number }>()
const route = useRoute()
const router = useRouter()

/** 分类治理工作台：规则 / 矩阵本地检索与 URL query 同步（刷新、分享链接可恢复） */
const DS_GOV_RULE_Q = 'dsGovRuleQ'
const DS_GOV_MATRIX_Q = 'dsGovMatrixQ'

const queryFirst = (value: unknown): string | undefined => {
  if (typeof value === 'string') return value
  if (Array.isArray(value) && typeof value[0] === 'string') return value[0]
  return undefined
}

const updateQuery = (patch: Record<string, string | undefined>) => {
  const nextQuery: Record<string, unknown> = { ...route.query, ...patch }
  Object.keys(nextQuery).forEach((key) => {
    if (nextQuery[key] === undefined) delete nextQuery[key]
  })
  const changed = Object.keys(patch).some((key) => {
    const current = queryFirst(route.query[key])
    const raw = nextQuery[key]
    const next = raw == null ? undefined : String(raw)
    return current !== next
  })
  if (changed) {
    router.replace({ query: nextQuery as Record<string, string | string[]> })
  }
}

const loading = ref(false)
const loadError = ref('')
const tab = ref('spaces')
/** 问卷与规则：子 Tab */
const questionnaireInnerTab = ref('questions')
/** 字段与主表：子 Tab */
const fieldGovInnerTab = ref('lifecycle')
/** 分类分级和要求治理：子 Tab */
const classificationInnerTab = ref('workbench')
/** 填报与审批中心：子 Tab */
const recordsInnerTab = ref('submissions')
/** 待审批事项：子 Tab */
const approvalsInnerTab = ref('usage-pending')
const spaces = ref<DataSecureProjectSpace[]>([])
const selectedSpaceId = ref<number | null>(null)
const questions = ref<DataSecureQuestion[]>([])
const assessments = ref<DataSecureAssessmentSubmission[]>([])
const fieldRequests = ref<DataSecureFieldRequest[]>([])
const bfOptionRequests = ref<DataSecureBusinessFunctionOptionRequest[]>([])
const fieldCatalog = ref<DataSecureFieldCatalogEntry[]>([])
const usageReports = ref<DataSecureFieldUsageReport[]>([])
const pendingUsageReports = ref<DataSecureFieldUsageReport[]>([])
const consolidateFilterKeys = ref<string[]>([])
const consolidateFilterVals = ref<string[]>([])
const exportConsolidatedLoading = ref(false)
const taxonomyNodesAll = ref<DataSecureTaxonomyNode[]>([])
const structuredClassGrades = ref<DataSecureFieldClassGrade[]>([])
const structuredSecurityReqs = ref<DataSecureFieldSecurityRequirement[]>([])
const structuredClassificationRules = ref<DataSecureClassificationRule[]>([])
const structuredClassificationMatrix = ref<DataSecureClassificationMatrix[]>([])
const structuredRuleKeyword = ref(queryFirst(route.query[DS_GOV_RULE_Q]) ?? '')
const structuredMatrixKeyword = ref(queryFirst(route.query[DS_GOV_MATRIX_Q]) ?? '')
const structuredEvalResult = ref<DataSecureFieldSecurityRequirementEvalResponse | null>(null)
const governanceChangeLogs = ref<DataSecureGovernanceChangeLog[]>([])
const changeLogDomain = ref('')
const changeLogPage = ref(1)
const changeLogPageSize = ref(20)
const changeLogTotal = ref(0)
const structuredEvalCatalogId = ref<number | null>(null)
const confidentialityGrades = ['C0-Public', 'C1-Internal', 'C2-Confidential', 'C3-Secret'] as const
const taxCreateForm = reactive({
  parent_id: null as number | null,
  name: '',
  node_key: ''
})
const gradeForm = reactive({
  catalog_entry_id: null as number | null,
  confidentiality_grade: 'C1-Internal',
  notes: ''
})
/** 密级绑定：分类级联路径（根→…→最细），与 el-cascader emitPath 一致 */
const gradeTaxonomyPath = ref<number[]>([])
const gradeTaxonomyCascaderProps = {
  value: 'id',
  label: 'name',
  children: 'children',
  emitPath: true,
  checkStrictly: true
}
const secCreateForm = reactive({
  catalog_entry_id: null as number | null,
  requirement_text: '',
  logic_expression: '',
  priority: 100
})

type SecPredKind =
  | 'grade_equals'
  | 'l1_node_key'
  | 'l2_node_key'
  | 'taxonomy_path_node_key'
  | 'lifecycle_field_contains'
type SecPredRow = { token: string; kind: SecPredKind; value: string; field_key?: string }
const secPredRows = ref<SecPredRow[]>([{ token: 'isC2', kind: 'grade_equals', value: 'C2-Confidential' }])
const securityPredicateKindOptions = [
  { label: '密级等于', value: 'grade_equals' },
  { label: '一级分类标识 等于', value: 'l1_node_key' },
  { label: '最细分类标识 等于', value: 'l2_node_key' },
  { label: '分类路径上任一层 node_key 等于', value: 'taxonomy_path_node_key' },
  { label: '生命周期字段值包含（模糊）', value: 'lifecycle_field_contains' }
]

type TaxonomyTreeNode = DataSecureTaxonomyNode & { children?: TaxonomyTreeNode[] }

const taxonomyTreeForGradeCascader = computed((): TaxonomyTreeNode[] => {
  const nodes = taxonomyNodesAll.value.filter((n) => n.is_active)
  const byId = new Map<number, TaxonomyTreeNode>()
  for (const n of nodes) {
    byId.set(n.id, { ...n, children: [] })
  }
  const roots: TaxonomyTreeNode[] = []
  for (const n of nodes) {
    const tn = byId.get(n.id)
    if (!tn) continue
    if (n.parent_id == null) {
      roots.push(tn)
    } else {
      const p = byId.get(n.parent_id)
      if (p) {
        if (!p.children) p.children = []
        p.children.push(tn)
      } else {
        roots.push(tn)
      }
    }
  }
  const sortRec = (arr: TaxonomyTreeNode[]) => {
    arr.sort((a, b) => (a.sort_order ?? 0) - (b.sort_order ?? 0) || a.id - b.id)
    for (const x of arr) {
      if (x.children?.length) sortRec(x.children)
    }
  }
  sortRec(roots)
  return roots
})

const taxonomyFlatParentOptions = computed(() => {
  const out: { id: number; label: string }[] = []
  const walk = (nodes: TaxonomyTreeNode[], depth: number) => {
    const pad = '　'.repeat(depth)
    for (const n of nodes) {
      out.push({ id: n.id, label: `${pad}${n.name}（${n.node_key}）` })
      if (n.children?.length) walk(n.children, depth + 1)
    }
  }
  walk(taxonomyTreeForGradeCascader.value, 0)
  return out
})

const filteredStructuredClassificationRules = computed(() => {
  const q = structuredRuleKeyword.value.trim().toLowerCase()
  if (!q) return structuredClassificationRules.value
  return structuredClassificationRules.value.filter((row) => {
    const text = `${row.keyword} ${row.category} ${row.level}`.toLowerCase()
    return text.includes(q)
  })
})

const filteredStructuredClassificationMatrix = computed(() => {
  const q = structuredMatrixKeyword.value.trim().toLowerCase()
  if (!q) return structuredClassificationMatrix.value
  return structuredClassificationMatrix.value.filter((row) => {
    const text = `${row.field_name} ${row.category} ${row.level}`.toLowerCase()
    return text.includes(q)
  })
})

/** 与后端列表/export 一致：priority 降序，其次 sort_order、id */
function cmpGovernancePrioThenSort<T extends { priority?: number; sort_order: number; id: number }>(a: T, b: T): number {
  const pd = (b.priority ?? 0) - (a.priority ?? 0)
  if (pd !== 0) return pd
  const sd = (a.sort_order ?? 0) - (b.sort_order ?? 0)
  if (sd !== 0) return sd
  return a.id - b.id
}

const questionsDisplayOrdered = computed(() =>
  [...questions.value].sort((a, b) => (a.sort_order ?? 0) - (b.sort_order ?? 0) || a.id - b.id)
)

const securityRequirementsOrdered = computed(() => [...structuredSecurityReqs.value].sort(cmpGovernancePrioThenSort))

const classificationRulesGovernanceOrder = computed(() =>
  [...structuredClassificationRules.value].sort(cmpGovernancePrioThenSort)
)

const classificationMatrixGovernanceOrder = computed(() =>
  [...structuredClassificationMatrix.value].sort(cmpGovernancePrioThenSort)
)

function taxonomySiblingsSorted(parentId: number | null | undefined): DataSecureTaxonomyNode[] {
  const p = parentId ?? null
  return taxonomyNodesAll.value
    .filter((n) => (n.parent_id ?? null) === p)
    .sort((a, b) => (a.sort_order ?? 0) - (b.sort_order ?? 0) || a.id - b.id)
}

function sameGovernancePriority(a: { priority?: number }, b: { priority?: number }): boolean {
  return (a.priority ?? 0) === (b.priority ?? 0)
}

watch(structuredRuleKeyword, (v) => {
  updateQuery({ [DS_GOV_RULE_Q]: v.length ? v : undefined })
})

watch(structuredMatrixKeyword, (v) => {
  updateQuery({ [DS_GOV_MATRIX_Q]: v.length ? v : undefined })
})

watch(
  () =>
    `${queryFirst(route.query[DS_GOV_RULE_Q]) ?? ''}\u0000${queryFirst(route.query[DS_GOV_MATRIX_Q]) ?? ''}`,
  () => {
    const rq = queryFirst(route.query[DS_GOV_RULE_Q]) ?? ''
    const mq = queryFirst(route.query[DS_GOV_MATRIX_Q]) ?? ''
    if (rq !== structuredRuleKeyword.value) structuredRuleKeyword.value = rq
    if (mq !== structuredMatrixKeyword.value) structuredMatrixKeyword.value = mq
  }
)

const legacyTaxonomyPathLabel = (row: DataSecureFieldClassGrade) => {
  const a = row.taxonomy_l1_name || '—'
  const b = row.taxonomy_l2_name
  if (!b) return a
  return `${a} / ${b}`
}

function taxonomyPathIdsFromGradeRow(g: DataSecureFieldClassGrade, nodes: DataSecureTaxonomyNode[]): number[] {
  if (g.taxonomy_path_ids?.length) return [...g.taxonomy_path_ids]
  if (!g.taxonomy_l2_id) {
    return g.taxonomy_l1_id != null ? [g.taxonomy_l1_id] : []
  }
  const byId = new Map(nodes.map((n) => [n.id, n]))
  const chainRev: number[] = []
  let cur: number | null | undefined = g.taxonomy_l2_id
  const seen = new Set<number>()
  while (cur != null) {
    if (seen.has(cur)) break
    seen.add(cur)
    chainRev.push(cur)
    cur = byId.get(cur)?.parent_id ?? null
  }
  chainRev.reverse()
  if (g.taxonomy_l1_id != null && chainRev.length && chainRev[0] !== g.taxonomy_l1_id) {
    return [g.taxonomy_l1_id, ...chainRev.filter((id) => id !== g.taxonomy_l1_id)]
  }
  return chainRev
}
const pendingFieldRequests = computed(() => fieldRequests.value.filter((item) => item.status === 'pending'))
const pendingBfOptionRequests = computed(() => bfOptionRequests.value.filter((item) => item.status === 'pending'))
const fieldCatalogQuery = ref('')
const recordSpaceId = ref<number | null>(null)
/** 过审大表导出目标空间（可与「填报记录」筛选独立） */
const exportConsolidatedSpaceId = ref<number | null>(null)
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)
const lifecycleLoading = ref(false)
const lifecycleSaving = ref(false)
const lifecycleCreating = ref(false)
const spaceForm = reactive<{ space_key: string; name: string; description: string; copy_from_project_space_id: number | null }>(
  { space_key: '', name: '', description: '', copy_from_project_space_id: null }
)
const questionForm = reactive({ question_key: '', title: '', help_text: '' })
const questionBatchText = ref('')
const questionHelpDialogVisible = ref(false)
const questionHelpSaving = ref(false)
const questionHelpEdit = ref<{ id: number; title: string; help_text: string } | null>(null)
const lifecycleFields = ref<FormFieldConfigItem[]>([])
const lifecycleFieldRows = ref<FieldConfigTableRow[]>([])
const newLifecycleField = reactive<{ field_key: string; label: string; input_type: FormFieldInputType }>({
  field_key: '',
  label: '',
  input_type: 'text',
})
const lifecycleBatchText = ref('')
/** 与后端 data_secure_dynamic_fields.FIELD_KEY_PATTERN 一致 */
const FIELD_KEY_PATTERN = /^[a-z][a-z0-9_]{0,63}$/
const spaceKeyTouched = ref(false)
const questionKeyTouched = ref(false)
const lifecycleFieldKeyTouched = ref(false)
const taxonomyNodeKeyTouched = ref(false)
const fieldInputTypeOptions: Array<{ label: string; value: FormFieldInputType }> = [
  { label: '单行文本', value: 'text' },
  { label: '多行文本', value: 'textarea' },
  { label: '单选', value: 'single_select' },
  { label: '多选', value: 'multi_select' },
]
/** 数据生命周期内置列：禁止删除且禁止与相邻行换位（可与 FieldConfigManagerTable 二 prop 共用） */
const lifecycleFieldDeleteProtectedKeys = ['field_name', 'business_function'] as const
const catalogExtraDialogVisible = ref(false)
const catalogExtraEditEntry = ref<DataSecureFieldCatalogEntry | null>(null)
const catalogExtraForm = ref<Record<string, any>>({})
const catalogExtraSaving = ref(false)
const lifecycleDynamicFieldsForCatalogEdit = computed(() =>
  lifecycleFields.value.filter((item) => !item.is_builtin || item.field_key === 'business_function')
)
const lifecyclePredicateFieldOptions = computed(() =>
  lifecycleDynamicFieldsForCatalogEdit.value.map((f) => ({ label: `${f.label} (${f.field_key})`, value: f.field_key }))
)
const consolidatedExportFieldKeyOptions = computed(() =>
  lifecycleDynamicFieldsForCatalogEdit.value.map((f) => ({ label: `${f.label} (${f.field_key})`, value: f.field_key }))
)
const lifecycleFieldValueRemoteLoading = ref(false)
const lifecycleFieldValueRemoteOptions = ref<Record<string, string[]>>({})
const manualCatalogDialogVisible = ref(false)
const manualCatalogFieldName = ref('')
const manualCatalogExtraFields = ref<Record<string, any>>({})
const manualCatalogSaving = ref(false)
const catalogCsvInputRef = ref<HTMLInputElement | null>(null)
const governanceTaxonomyCsvInputRef = ref<HTMLInputElement | null>(null)
const governanceClassGradeCsvInputRef = ref<HTMLInputElement | null>(null)
const governanceSecurityCsvInputRef = ref<HTMLInputElement | null>(null)
/** 高级配置：与 CSV 文件导入相同表头，粘贴后「从文本导入」 */
const governanceTaxonomyBatchText = ref('')
const governanceClassGradeBatchText = ref('')
const governanceSecurityBatchText = ref('')
const configJsonInputRef = ref<HTMLInputElement | null>(null)
const batchDeleteJsonText = ref('')
const ruleForm = reactive<{ min_yes_count: number; logic_operator: 'and' | 'or'; question_keys: string[]; logic_expression: string; notes: string }>({
  min_yes_count: 1,
  logic_operator: 'and',
  question_keys: [],
  logic_expression: '',
  notes: '',
})
const availableQuestionKeys = computed(() => new Set(questions.value.filter((item) => item.is_active).map((item) => item.question_key)))

type LocalExprValidation = { valid: boolean; message: string }

const tokenizeExpressionLocal = (expression: string): string[] => {
  const src = expression.trim()
  const tokens: string[] = []
  let i = 0
  while (i < src.length) {
    const ch = src[i]
    if (/\s/.test(ch)) {
      i += 1
      continue
    }
    if (ch === '(' || ch === ')') {
      tokens.push(ch)
      i += 1
      continue
    }
    let j = i
    while (j < src.length && /[A-Za-z0-9_-]/.test(src[j])) j += 1
    if (j === i) return []
    tokens.push(src.slice(i, j))
    i = j
  }
  return tokens
}

const validateExpressionLocal = (expression: string, validKeys: Set<string>): LocalExprValidation => {
  const tokens = tokenizeExpressionLocal(expression)
  if (!tokens.length) return { valid: false, message: '表达式包含非法字符或为空。' }
  const precedence: Record<string, number> = { or: 1, and: 2 }
  const output: string[] = []
  const ops: string[] = []
  for (const token of tokens) {
    const low = token.toLowerCase()
    if (token === '(') {
      ops.push(token)
      continue
    }
    if (token === ')') {
      while (ops.length && ops[ops.length - 1] !== '(') output.push(ops.pop() as string)
      if (!ops.length || ops[ops.length - 1] !== '(') return { valid: false, message: '括号不匹配。' }
      ops.pop()
      continue
    }
    if (low === 'and' || low === 'or') {
      while (
        ops.length &&
        (ops[ops.length - 1] === 'and' || ops[ops.length - 1] === 'or') &&
        precedence[ops[ops.length - 1]] >= precedence[low]
      ) output.push(ops.pop() as string)
      ops.push(low)
      continue
    }
    if (!validKeys.has(token)) return { valid: false, message: `表达式引用了不存在的题目标识：${token}` }
    output.push(token)
  }
  while (ops.length) {
    const op = ops.pop() as string
    if (op === '(') return { valid: false, message: '括号不匹配。' }
    output.push(op)
  }
  let depth = 0
  for (const token of output) {
    if (token === 'and' || token === 'or') {
      if (depth < 2) return { valid: false, message: '表达式运算符位置不合法。' }
      depth -= 1
    } else {
      depth += 1
    }
  }
  if (depth !== 1) return { valid: false, message: '表达式结构不完整。' }
  return { valid: true, message: '表达式格式正确。' }
}

const expressionValidation = computed<LocalExprValidation>(() => {
  const expression = (ruleForm.logic_expression || '').trim()
  if (!expression) return { valid: false, message: '请填写逻辑表达式。' }
  return validateExpressionLocal(expression, availableQuestionKeys.value)
})

const secPredicateTokenList = computed(() => {
  const seen = new Set<string>()
  const out: string[] = []
  for (const r of secPredRows.value) {
    const t = (r.token || '').trim()
    if (!t || seen.has(t)) continue
    seen.add(t)
    out.push(t)
  }
  return out
})

const validSecPredKeySet = computed(() => new Set(secPredicateTokenList.value))

const secRequirementExprValidation = computed<LocalExprValidation>(() => {
  const expression = (secCreateForm.logic_expression || '').trim()
  if (!expression) {
    return { valid: false, message: '请填写逻辑表达式，或使用下方构建器与谓词标识拼接。' }
  }
  return validateExpressionLocal(expression, validSecPredKeySet.value)
})

const unmatchedSecReqParenHint = computed(() => {
  const text = secCreateForm.logic_expression || ''
  let depth = 0
  for (const ch of text) {
    if (ch === '(') depth += 1
    if (ch === ')') depth -= 1
  }
  if (depth === 0) return '括号已配平'
  if (depth > 0) return `还缺少 ${depth} 个右括号 )`
  return `右括号过多（多出 ${Math.abs(depth)} 个）`
})

const unmatchedParenHint = computed(() => {
  const text = ruleForm.logic_expression || ''
  let depth = 0
  for (const ch of text) {
    if (ch === '(') depth += 1
    if (ch === ')') depth -= 1
  }
  if (depth === 0) return '括号已配平'
  if (depth > 0) return `还缺少 ${depth} 个右括号 )`
  return `右括号过多（多出 ${Math.abs(depth)} 个）`
})

const loadSpaces = async () => {
  const res = await toolsApi.getDataSecureProjectSpaces(props.toolId, 0, 100)
  spaces.value = res.items
  const ids = new Set(spaces.value.map((s) => s.id))
  if (selectedSpaceId.value != null && !ids.has(selectedSpaceId.value)) {
    selectedSpaceId.value = spaces.value.length ? spaces.value[0].id : null
  }
  if (selectedSpaceId.value == null && spaces.value.length) {
    selectedSpaceId.value = spaces.value[0].id
  }
  if (recordSpaceId.value == null && selectedSpaceId.value != null) {
    recordSpaceId.value = selectedSpaceId.value
  }
  const activeFirst = spaces.value.find((s) => s.is_active) || spaces.value[0]
  if (exportConsolidatedSpaceId.value != null && !ids.has(exportConsolidatedSpaceId.value)) {
    exportConsolidatedSpaceId.value = activeFirst?.id ?? null
  }
  if (exportConsolidatedSpaceId.value == null && activeFirst) {
    exportConsolidatedSpaceId.value = activeFirst.id
  }
}
const loadQuestionnaireData = async () => {
  if (!selectedSpaceId.value) return
  const qRes = await toolsApi.getDataSecureQuestions(props.toolId, selectedSpaceId.value, 0, 200)
  questions.value = qRes.items
  const rule = await toolsApi.getDataSecureRelevanceRule(props.toolId, selectedSpaceId.value)
  ruleForm.min_yes_count = rule?.min_yes_count ?? 1
  ruleForm.logic_operator = rule?.logic_operator || 'and'
  ruleForm.question_keys = rule?.question_keys || []
  ruleForm.logic_expression = rule?.logic_expression || ''
  ruleForm.notes = rule?.notes || ''
}
const loadPendingUsageReports = async () => {
  const sid = recordSpaceId.value ?? selectedSpaceId.value
  if (!sid) {
    pendingUsageReports.value = []
    return
  }
  const res = await toolsApi.getDataSecureFieldUsageReports(props.toolId, {
    project_space_id: sid,
    review_status: 'pending',
    skip: 0,
    limit: 100
  })
  pendingUsageReports.value = res.items
}

const reviewUsageReportRow = async (row: DataSecureFieldUsageReport, status: 'approved' | 'rejected') => {
  let review_notes: string | undefined
  if (status === 'rejected') {
    try {
      const { value } = await ElMessageBox.prompt('请输入驳回说明（可选）', '驳回填报工单', {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        inputPlaceholder: '说明原因，便于用户修改后重提'
      })
      review_notes = (value || '').trim() || undefined
    } catch {
      return
    }
  }
  await toolsApi.reviewDataSecureFieldUsageReport(props.toolId, row.id, { status, review_notes })
  ElMessage.success(status === 'approved' ? '已通过审批' : '已驳回')
  await loadPendingUsageReports()
}

const exportConsolidatedMaster = async () => {
  if (!exportConsolidatedSpaceId.value) return ElMessage.warning('请选择导出目标项目空间')
  exportConsolidatedLoading.value = true
  try {
    const fk = consolidateFilterKeys.value.map((x) => String(x).trim()).filter(Boolean)
    const fv = consolidateFilterVals.value.map((x) => String(x).trim()).filter(Boolean)
    const res = await toolsApi.exportDataSecureApprovedConsolidated(props.toolId, {
      project_space_id: exportConsolidatedSpaceId.value,
      mine: false,
      filter_field_key: fk.length ? fk : undefined,
      filter_value_contains: fv.length ? fv : undefined
    })
    downloadApprovedConsolidatedCsv(`过审填报大表-空间${exportConsolidatedSpaceId.value}.csv`, res.items)
    ElMessage.success('已开始下载')
  } catch (error: any) {
    ElMessage.error(error?.message || '导出失败')
  } finally {
    exportConsolidatedLoading.value = false
  }
}

const loadAssessmentRows = async () => {
  const res = await toolsApi.getDataSecureAssessments(props.toolId, recordSpaceId.value || undefined, (page.value - 1) * pageSize.value, pageSize.value)
  assessments.value = res.items
  total.value = res.total
}

const loadSubmissionsBlock = async () => {
  await loadAssessmentRows()
  await loadUsageReports()
}

const loadApprovalsBlock = async () => {
  await loadPendingUsageReports()
  await Promise.all([loadFieldRequests(), loadBfOptionRequests()])
}

/** 按「填报与审批中心」当前子 Tab 拉取列表（避免无关接口）。 */
const loadRecordsPaneData = async () => {
  if (recordsInnerTab.value === 'submissions') {
    await loadSubmissionsBlock()
  } else if (recordsInnerTab.value === 'approvals') {
    await loadApprovalsBlock()
  }
}

const onRecordSpaceFilterChange = async () => {
  page.value = 1
  await loadRecordsPaneData()
}
const loadLifecycleFieldConfigs = async () => {
  if (!selectedSpaceId.value) return
  lifecycleLoading.value = true
  try {
    const res = await toolsApi.getDataSecureLifecycleFieldConfigs(props.toolId, selectedSpaceId.value)
    lifecycleFields.value = res.items
    lifecycleFieldRows.value = res.items.map((item) => ({
      ...item,
      allowed_values_text: (item.allowed_values || []).join(', ')
    }))
  } finally {
    lifecycleLoading.value = false
  }
}
const loadFieldRequests = async () => {
  const res = await toolsApi.getDataSecureFieldRequests(props.toolId, { limit: 100 })
  fieldRequests.value = res.items
}
const loadBfOptionRequests = async () => {
  const res = await toolsApi.getDataSecureBusinessFunctionOptionRequests(props.toolId, { limit: 100 })
  bfOptionRequests.value = res.items
}
const loadFieldCatalog = async () => {
  if (!selectedSpaceId.value) return
  const res = await toolsApi.getDataSecureFieldCatalog(
    props.toolId,
    selectedSpaceId.value,
    0,
    200,
    fieldCatalogQuery.value || undefined
  )
  fieldCatalog.value = res.items
}

const collectDistinctOptionValuesByFieldKey = async (fieldKey: string): Promise<string[]> => {
  if (!selectedSpaceId.value) return []
  await loadFieldCatalog()
  const values = new Set<string>()
  for (const entry of fieldCatalog.value) {
    if (fieldKey === 'field_name') {
      const name = (entry.field_name || '').trim()
      if (name) values.add(name)
      continue
    }
    const raw = entry.extra_fields?.[fieldKey]
    if (raw == null) continue
    if (Array.isArray(raw)) {
      for (const v of raw) {
        const text = String(v || '').trim()
        if (text) values.add(text)
      }
      continue
    }
    const text = String(raw || '').trim()
    if (text) values.add(text)
  }
  return Array.from(values)
}
const loadUsageReports = async () => {
  const sid = recordSpaceId.value ?? selectedSpaceId.value
  const res = await toolsApi.getDataSecureFieldUsageReports(props.toolId, { project_space_id: sid || undefined, limit: 100 })
  usageReports.value = res.items
}

const lifecycleValueRowKey = (row: SecPredRow) => `${(row.token || '').trim()}::${(row.field_key || '').trim()}`

const lifecycleFieldValueRemoteOptionsForRow = (row: SecPredRow): string[] => {
  const key = lifecycleValueRowKey(row)
  const options = lifecycleFieldValueRemoteOptions.value[key] || []
  const current = (row.value || '').trim()
  if (!current) return options
  return options.includes(current) ? options : [current, ...options]
}

const searchLifecycleFieldValueOptions = async (row: SecPredRow, keyword: string) => {
  if (!selectedSpaceId.value) return
  const fieldKey = (row.field_key || '').trim()
  if (!fieldKey) {
    lifecycleFieldValueRemoteOptions.value[lifecycleValueRowKey(row)] = []
    return
  }
  lifecycleFieldValueRemoteLoading.value = true
  try {
    const res = await toolsApi.getDataSecureFieldCatalogValueOptions(props.toolId, {
      project_space_id: selectedSpaceId.value,
      field_key: fieldKey,
      q: (keyword || '').trim() || undefined,
      limit: 30
    })
    lifecycleFieldValueRemoteOptions.value[lifecycleValueRowKey(row)] = res.options || []
  } finally {
    lifecycleFieldValueRemoteLoading.value = false
  }
}

const onLifecycleValueDropdownVisible = (row: SecPredRow, visible: boolean) => {
  if (!visible) return
  if (!row.field_key) return
  void searchLifecycleFieldValueOptions(row, row.value || '')
}

const makeLifecycleValueRemoteMethod = (row: SecPredRow) => {
  return (keyword: string) => {
    void searchLifecycleFieldValueOptions(row, keyword)
  }
}

const handleLifecycleValueDropdownVisible = (row: SecPredRow, visible: unknown) => {
  onLifecycleValueDropdownVisible(row, Boolean(visible))
}

const lifecycleFieldKeyRemoteOptions = ref<Record<string, string[]>>({})
const lifecycleFieldKeyRowKey = (row: SecPredRow) => `${(row.token || '').trim()}::fk`

const lifecycleFieldKeyLabel = (fieldKey: string) => {
  const f = lifecyclePredicateFieldOptions.value.find((o) => o.value === fieldKey)
  return f ? f.label : fieldKey
}

const lifecycleFieldKeyOptionsForRow = (row: SecPredRow): string[] => {
  const key = lifecycleFieldKeyRowKey(row)
  const opts = lifecycleFieldKeyRemoteOptions.value[key] || []
  const cur = (row.field_key || '').trim()
  if (!cur) return opts
  return opts.includes(cur) ? opts : [cur, ...opts]
}

const searchLifecycleFieldKeyOptions = (row: SecPredRow, keyword: string) => {
  const s = (keyword || '').trim().toLowerCase()
  const base = lifecyclePredicateFieldOptions.value
  const filtered = !s
    ? base.slice(0, 80)
    : base.filter((o) => o.label.toLowerCase().includes(s) || o.value.toLowerCase().includes(s)).slice(0, 80)
  lifecycleFieldKeyRemoteOptions.value[lifecycleFieldKeyRowKey(row)] = filtered.map((o) => o.value)
}

const makeLifecycleFieldKeyRemoteMethod = (row: SecPredRow) => (keyword: string) => {
  searchLifecycleFieldKeyOptions(row, keyword)
}

const handleLifecycleFieldKeyDropdownVisible = (row: SecPredRow, visible: unknown) => {
  if (!visible) return
  searchLifecycleFieldKeyOptions(row, row.field_key || '')
}

const taxonomyNodeKeyRemoteOptions = ref<Record<string, string[]>>({})
const taxonomyNodeKeyRowKey = (row: SecPredRow) => `${(row.token || '').trim()}::tx`

const taxonomyNodeKeyOptionsForRow = (row: SecPredRow): string[] => {
  const key = taxonomyNodeKeyRowKey(row)
  const opts = taxonomyNodeKeyRemoteOptions.value[key] || []
  const cur = (row.value || '').trim()
  if (!cur) return opts
  return opts.includes(cur) ? opts : [cur, ...opts]
}

const searchTaxonomyNodeKeyOptions = (row: SecPredRow, keyword: string) => {
  const s = (keyword || '').trim().toLowerCase()
  const keys = [
    ...new Set(
      taxonomyNodesAll.value
        .filter((n) => n.is_active)
        .map((n) => (n.node_key || '').trim())
        .filter(Boolean)
    )
  ]
  const filtered = !s ? keys.slice(0, 80) : keys.filter((k) => k.toLowerCase().includes(s)).slice(0, 80)
  taxonomyNodeKeyRemoteOptions.value[taxonomyNodeKeyRowKey(row)] = filtered
}

const makeTaxonomyNodeKeyRemoteMethod = (row: SecPredRow) => (keyword: string) => {
  searchTaxonomyNodeKeyOptions(row, keyword)
}

const handleTaxonomyNodeKeyDropdownVisible = (row: SecPredRow, visible: unknown) => {
  if (!visible) return
  searchTaxonomyNodeKeyOptions(row, row.value || '')
}

const loadFieldGovernanceData = async () => {
  await loadLifecycleFieldConfigs()
  await loadFieldCatalog()
  await Promise.all([loadFieldRequests(), loadBfOptionRequests()])
}
const loadStructuredGovernanceData = async () => {
  if (!selectedSpaceId.value) return
  await loadFieldCatalog()
  const sid = selectedSpaceId.value
  const [tRes, gRes, sRes, rulesRes, matrixRes] = await Promise.all([
    toolsApi.getDataSecureTaxonomyNodes(props.toolId, sid, { limit: 200 }),
    toolsApi.getDataSecureFieldClassGrades(props.toolId, sid, 0, 200),
    toolsApi.getDataSecureFieldSecurityRequirements(props.toolId, sid, { limit: 200 }),
    toolsApi.getDataSecureClassificationRules(props.toolId, sid, 0, 200),
    toolsApi.getDataSecureClassificationMatrix(props.toolId, sid, 0, 200)
  ])
  taxonomyNodesAll.value = tRes.items
  structuredClassGrades.value = gRes.items
  structuredSecurityReqs.value = sRes.items
  structuredClassificationRules.value = rulesRes.items
  structuredClassificationMatrix.value = matrixRes.items
}

const askChangeReason = async (actionLabel: string): Promise<string | null> => {
  try {
    const { value } = await ElMessageBox.prompt(`请填写本次「${actionLabel}」的变更原因（至少 5 个字）`, '填写变更原因', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      inputType: 'textarea',
      inputPlaceholder: '例如：为统一口径，新增并规范业务功能选项',
      inputValidator: (v: string) => {
        if (!v || v.trim().length < 5) return '请至少填写 5 个字'
        return true
      }
    })
    return (value || '').trim()
  } catch {
    return null
  }
}

const loadGovernanceChangeLogs = async () => {
  if (!selectedSpaceId.value) {
    governanceChangeLogs.value = []
    changeLogTotal.value = 0
    return
  }
  const res = await toolsApi.getDataSecureGovernanceChangeLogs(props.toolId, {
    project_space_id: selectedSpaceId.value,
    domain: changeLogDomain.value || undefined,
    skip: (changeLogPage.value - 1) * changeLogPageSize.value,
    limit: changeLogPageSize.value
  })
  governanceChangeLogs.value = res.items
  changeLogTotal.value = res.total
}

const onChangeLogDomainChange = async () => {
  changeLogPage.value = 1
  await loadGovernanceChangeLogs()
}

const onChangeLogPageSizeChange = async (size: number) => {
  changeLogPageSize.value = size
  changeLogPage.value = 1
  await loadGovernanceChangeLogs()
}

const onStructuredSpaceChange = async () => {
  structuredEvalResult.value = null
  gradeTaxonomyPath.value = []
  await loadStructuredGovernanceData()
}

watch(
  () => [gradeForm.catalog_entry_id, structuredClassGrades.value, taxonomyNodesAll.value] as const,
  () => {
    const cid = gradeForm.catalog_entry_id
    if (cid == null) {
      gradeTaxonomyPath.value = []
      return
    }
    const g = structuredClassGrades.value.find((x) => x.catalog_entry_id === cid)
    if (!g) {
      gradeTaxonomyPath.value = []
      return
    }
    gradeTaxonomyPath.value = taxonomyPathIdsFromGradeRow(g, taxonomyNodesAll.value)
  }
)

const submitTaxonomyCreate = async () => {
  if (!selectedSpaceId.value) return
  const name = taxCreateForm.name.trim()
  let nodeKey = taxCreateForm.node_key.trim()
  if (!name) {
    ElMessage.warning('请填写节点名称')
    return
  }
  if (!nodeKey) {
    nodeKey = await suggestKeyFromSource(name, 'taxonomy_node_key')
    taxCreateForm.node_key = nodeKey
  }
  if (!nodeKey) {
    ElMessage.warning('无法生成节点标识，请检查名称或手动填写')
    return
  }
  const changeReason = await askChangeReason('新增分类节点')
  if (!changeReason) return
  const sibs = taxonomySiblingsSorted(taxCreateForm.parent_id)
  const maxTaxSo = sibs.reduce((m, n) => Math.max(m, n.sort_order ?? 0), -1)
  await toolsApi.createDataSecureTaxonomyNode(props.toolId, {
    project_space_id: selectedSpaceId.value,
    parent_id: taxCreateForm.parent_id ?? undefined,
    name,
    node_key: nodeKey,
    sort_order: maxTaxSo + 1,
    change_reason: changeReason
  })
  ElMessage.success('已新增分类节点')
  taxCreateForm.name = ''
  taxCreateForm.node_key = ''
  taxCreateForm.parent_id = null
  taxonomyNodeKeyTouched.value = false
  await loadStructuredGovernanceData()
}

const deactivateTaxonomyNode = async (row: DataSecureTaxonomyNode) => {
  try {
    await ElMessageBox.confirm(
      `确定停用分类节点「${row.name}」？其下所有子节点将一并停用。`,
      '停用',
      { type: 'warning' }
    )
  } catch {
    return
  }
  const changeReason = await askChangeReason(`停用分类节点「${row.name}」`)
  if (!changeReason) return
  await toolsApi.updateDataSecureTaxonomyNode(props.toolId, row.id, { is_active: false, change_reason: changeReason })
  ElMessage.success('已停用')
  await loadStructuredGovernanceData()
}

const confirmDeleteTaxonomyNode = async (row: DataSecureTaxonomyNode) => {
  try {
    await ElMessageBox.confirm(
      `确定删除分类节点「${row.name}」？删除后不可恢复。`,
      '删除分类节点',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' }
    )
  } catch {
    return
  }
  const changeReason = await askChangeReason(`删除分类节点「${row.name}」`)
  if (!changeReason) return
  await toolsApi.deleteDataSecureTaxonomyNode(props.toolId, row.id, changeReason)
  ElMessage.success('分类节点已删除')
  await loadStructuredGovernanceData()
}

const submitStructuredGrade = async () => {
  if (!selectedSpaceId.value || gradeForm.catalog_entry_id == null) {
    ElMessage.warning('请选择数据字段主表行')
    return
  }
  const changeReason = await askChangeReason('保存密级与分类绑定')
  if (!changeReason) return
  const path = gradeTaxonomyPath.value
  let taxonomy_l1_id: number | undefined
  let taxonomy_l2_id: number | undefined
  if (!path?.length) {
    taxonomy_l1_id = undefined
    taxonomy_l2_id = undefined
  } else if (path.length === 1) {
    taxonomy_l1_id = path[0]
    taxonomy_l2_id = undefined
  } else {
    taxonomy_l1_id = path[0]
    taxonomy_l2_id = path[path.length - 1]
  }
  await toolsApi.upsertDataSecureFieldClassGrade(props.toolId, {
    project_space_id: selectedSpaceId.value,
    catalog_entry_id: gradeForm.catalog_entry_id,
    taxonomy_l1_id,
    taxonomy_l2_id,
    confidentiality_grade: gradeForm.confidentiality_grade,
    notes: gradeForm.notes?.trim() || undefined,
    change_reason: changeReason
  })
  ElMessage.success('已保存密级与分类绑定')
  await loadStructuredGovernanceData()
}

const deleteStructuredGrade = async (row: DataSecureFieldClassGrade) => {
  try {
    await ElMessageBox.confirm(`确定删除字段「${row.field_name}」在分类分级和要求治理中的分级绑定？`, '删除', {
      type: 'warning'
    })
  } catch {
    return
  }
  const changeReason = await askChangeReason(`删除字段「${row.field_name}」的密级绑定`)
  if (!changeReason) return
  await toolsApi.deleteDataSecureFieldClassGrade(props.toolId, row.catalog_entry_id, changeReason)
  ElMessage.success('已删除')
  await loadStructuredGovernanceData()
}

const deleteStructuredSecurityReq = async (row: DataSecureFieldSecurityRequirement) => {
  try {
    await ElMessageBox.confirm('确定删除该条安全要求？删除后不可恢复。', '删除', { type: 'warning' })
  } catch {
    return
  }
  const changeReason = await askChangeReason(`删除安全要求 #${row.id}`)
  if (!changeReason) return
  await toolsApi.deleteDataSecureFieldSecurityRequirement(props.toolId, row.id, changeReason)
  ElMessage.success('安全要求已删除')
  await loadStructuredGovernanceData()
}

const toggleStructuredSecurityReq = async (row: DataSecureFieldSecurityRequirement) => {
  const action = row.is_active ? '停用' : '启用'
  const changeReason = await askChangeReason(`${action}安全要求 #${row.id}`)
  if (!changeReason) return
  await toolsApi.updateDataSecureFieldSecurityRequirement(props.toolId, row.id, {
    is_active: !row.is_active,
    change_reason: changeReason
  })
  ElMessage.success(`安全要求已${action}`)
  await loadStructuredGovernanceData()
}

const toggleStructuredClassificationRule = async (row: DataSecureClassificationRule) => {
  const action = row.is_active ? '停用' : '启用'
  const changeReason = await askChangeReason(`${action}分类分级规则 #${row.id}`)
  if (!changeReason) return
  await toolsApi.updateDataSecureClassificationRule(props.toolId, {
    id: row.id,
    is_active: !row.is_active,
    change_reason: changeReason
  })
  ElMessage.success(`分类分级规则已${action}`)
  await loadStructuredGovernanceData()
}

const deleteStructuredClassificationRule = async (row: DataSecureClassificationRule) => {
  try {
    await ElMessageBox.confirm(`确定删除分类分级规则「${row.keyword}」？删除后不可恢复。`, '删除', { type: 'warning' })
  } catch {
    return
  }
  const changeReason = await askChangeReason(`删除分类分级规则 #${row.id}`)
  if (!changeReason) return
  await toolsApi.deleteDataSecureClassificationRule(props.toolId, row.id, changeReason)
  ElMessage.success('分类分级规则已删除')
  await loadStructuredGovernanceData()
}

const toggleStructuredClassificationMatrix = async (row: DataSecureClassificationMatrix) => {
  const action = row.is_active ? '停用' : '启用'
  const changeReason = await askChangeReason(`${action}显式分类矩阵 #${row.id}`)
  if (!changeReason) return
  await toolsApi.updateDataSecureClassificationMatrix(props.toolId, {
    id: row.id,
    is_active: !row.is_active,
    change_reason: changeReason
  })
  ElMessage.success(`显式分类矩阵已${action}`)
  await loadStructuredGovernanceData()
}

const deleteStructuredClassificationMatrix = async (row: DataSecureClassificationMatrix) => {
  try {
    await ElMessageBox.confirm(`确定删除显式分类矩阵「${row.field_name}」？删除后不可恢复。`, '删除', { type: 'warning' })
  } catch {
    return
  }
  const changeReason = await askChangeReason(`删除显式分类矩阵 #${row.id}`)
  if (!changeReason) return
  await toolsApi.deleteDataSecureClassificationMatrix(props.toolId, row.id, changeReason)
  ElMessage.success('显式分类矩阵已删除')
  await loadStructuredGovernanceData()
}

const moveQuestionOrderUp = async (row: DataSecureQuestion) => {
  const list = questionsDisplayOrdered.value
  const i = list.findIndex((q) => q.id === row.id)
  if (i <= 0) return
  const a = list[i - 1]
  const b = list[i]
  const sa = a.sort_order ?? 0
  const sb = b.sort_order ?? 0
  await toolsApi.updateDataSecureQuestion(props.toolId, { id: a.id, sort_order: sb })
  await toolsApi.updateDataSecureQuestion(props.toolId, { id: b.id, sort_order: sa })
  await loadQuestionnaireData()
}

const moveQuestionOrderDown = async (row: DataSecureQuestion) => {
  const list = questionsDisplayOrdered.value
  const i = list.findIndex((q) => q.id === row.id)
  if (i < 0 || i >= list.length - 1) return
  const a = list[i]
  const b = list[i + 1]
  const sa = a.sort_order ?? 0
  const sb = b.sort_order ?? 0
  await toolsApi.updateDataSecureQuestion(props.toolId, { id: a.id, sort_order: sb })
  await toolsApi.updateDataSecureQuestion(props.toolId, { id: b.id, sort_order: sa })
  await loadQuestionnaireData()
}

const isTaxonomyNodeMoveUpDisabled = (row: DataSecureTaxonomyNode) => {
  const sibs = taxonomySiblingsSorted(row.parent_id)
  const i = sibs.findIndex((n) => n.id === row.id)
  return i <= 0
}

const isTaxonomyNodeMoveDownDisabled = (row: DataSecureTaxonomyNode) => {
  const sibs = taxonomySiblingsSorted(row.parent_id)
  const i = sibs.findIndex((n) => n.id === row.id)
  return i < 0 || i >= sibs.length - 1
}

const moveTaxonomyNodeUp = async (row: DataSecureTaxonomyNode) => {
  const sibs = taxonomySiblingsSorted(row.parent_id)
  const i = sibs.findIndex((n) => n.id === row.id)
  if (i <= 0) return
  const a = sibs[i - 1]
  const b = sibs[i]
  const reason = await askChangeReason('调整分类节点顺序')
  if (!reason) return
  const sa = a.sort_order ?? 0
  const sb = b.sort_order ?? 0
  await toolsApi.updateDataSecureTaxonomyNode(props.toolId, a.id, { sort_order: sb, change_reason: reason })
  await toolsApi.updateDataSecureTaxonomyNode(props.toolId, b.id, { sort_order: sa, change_reason: reason })
  await loadStructuredGovernanceData()
}

const moveTaxonomyNodeDown = async (row: DataSecureTaxonomyNode) => {
  const sibs = taxonomySiblingsSorted(row.parent_id)
  const i = sibs.findIndex((n) => n.id === row.id)
  if (i < 0 || i >= sibs.length - 1) return
  const a = sibs[i]
  const b = sibs[i + 1]
  const reason = await askChangeReason('调整分类节点顺序')
  if (!reason) return
  const sa = a.sort_order ?? 0
  const sb = b.sort_order ?? 0
  await toolsApi.updateDataSecureTaxonomyNode(props.toolId, a.id, { sort_order: sb, change_reason: reason })
  await toolsApi.updateDataSecureTaxonomyNode(props.toolId, b.id, { sort_order: sa, change_reason: reason })
  await loadStructuredGovernanceData()
}

const isSecurityRequirementMoveUpDisabled = (row: DataSecureFieldSecurityRequirement) => {
  const list = securityRequirementsOrdered.value
  const i = list.findIndex((r) => r.id === row.id)
  if (i <= 0) return true
  return !sameGovernancePriority(list[i], list[i - 1])
}

const isSecurityRequirementMoveDownDisabled = (row: DataSecureFieldSecurityRequirement) => {
  const list = securityRequirementsOrdered.value
  const i = list.findIndex((r) => r.id === row.id)
  if (i < 0 || i >= list.length - 1) return true
  return !sameGovernancePriority(list[i], list[i + 1])
}

const moveSecurityRequirementUp = async (row: DataSecureFieldSecurityRequirement) => {
  const list = securityRequirementsOrdered.value
  const i = list.findIndex((r) => r.id === row.id)
  if (i <= 0) return
  const a = list[i - 1]
  const b = list[i]
  if (!sameGovernancePriority(a, b)) return
  const reason = await askChangeReason('调整安全要求顺序')
  if (!reason) return
  const sa = a.sort_order ?? 0
  const sb = b.sort_order ?? 0
  await toolsApi.updateDataSecureFieldSecurityRequirement(props.toolId, a.id, { sort_order: sb, change_reason: reason })
  await toolsApi.updateDataSecureFieldSecurityRequirement(props.toolId, b.id, { sort_order: sa, change_reason: reason })
  await loadStructuredGovernanceData()
}

const moveSecurityRequirementDown = async (row: DataSecureFieldSecurityRequirement) => {
  const list = securityRequirementsOrdered.value
  const i = list.findIndex((r) => r.id === row.id)
  if (i < 0 || i >= list.length - 1) return
  const a = list[i]
  const b = list[i + 1]
  if (!sameGovernancePriority(a, b)) return
  const reason = await askChangeReason('调整安全要求顺序')
  if (!reason) return
  const sa = a.sort_order ?? 0
  const sb = b.sort_order ?? 0
  await toolsApi.updateDataSecureFieldSecurityRequirement(props.toolId, a.id, { sort_order: sb, change_reason: reason })
  await toolsApi.updateDataSecureFieldSecurityRequirement(props.toolId, b.id, { sort_order: sa, change_reason: reason })
  await loadStructuredGovernanceData()
}

const isClassificationRuleMoveUpDisabled = (row: DataSecureClassificationRule) => {
  if (structuredRuleKeyword.value.trim()) return true
  const list = classificationRulesGovernanceOrder.value
  const i = list.findIndex((r) => r.id === row.id)
  if (i <= 0) return true
  return !sameGovernancePriority(list[i], list[i - 1])
}

const isClassificationRuleMoveDownDisabled = (row: DataSecureClassificationRule) => {
  if (structuredRuleKeyword.value.trim()) return true
  const list = classificationRulesGovernanceOrder.value
  const i = list.findIndex((r) => r.id === row.id)
  if (i < 0 || i >= list.length - 1) return true
  return !sameGovernancePriority(list[i], list[i + 1])
}

const moveClassificationRuleUp = async (row: DataSecureClassificationRule) => {
  if (structuredRuleKeyword.value.trim()) {
    ElMessage.warning('请先清空规则检索再调整顺序')
    return
  }
  const list = classificationRulesGovernanceOrder.value
  const i = list.findIndex((r) => r.id === row.id)
  if (i <= 0) return
  const a = list[i - 1]
  const b = list[i]
  if (!sameGovernancePriority(a, b)) return
  const reason = await askChangeReason('调整关键词分类分级规则顺序')
  if (!reason) return
  const sa = a.sort_order ?? 0
  const sb = b.sort_order ?? 0
  await toolsApi.updateDataSecureClassificationRule(props.toolId, {
    id: a.id,
    sort_order: sb,
    change_reason: reason
  })
  await toolsApi.updateDataSecureClassificationRule(props.toolId, {
    id: b.id,
    sort_order: sa,
    change_reason: reason
  })
  await loadStructuredGovernanceData()
}

const moveClassificationRuleDown = async (row: DataSecureClassificationRule) => {
  if (structuredRuleKeyword.value.trim()) {
    ElMessage.warning('请先清空规则检索再调整顺序')
    return
  }
  const list = classificationRulesGovernanceOrder.value
  const i = list.findIndex((r) => r.id === row.id)
  if (i < 0 || i >= list.length - 1) return
  const a = list[i]
  const b = list[i + 1]
  if (!sameGovernancePriority(a, b)) return
  const reason = await askChangeReason('调整关键词分类分级规则顺序')
  if (!reason) return
  const sa = a.sort_order ?? 0
  const sb = b.sort_order ?? 0
  await toolsApi.updateDataSecureClassificationRule(props.toolId, {
    id: a.id,
    sort_order: sb,
    change_reason: reason
  })
  await toolsApi.updateDataSecureClassificationRule(props.toolId, {
    id: b.id,
    sort_order: sa,
    change_reason: reason
  })
  await loadStructuredGovernanceData()
}

const isClassificationMatrixMoveUpDisabled = (row: DataSecureClassificationMatrix) => {
  if (structuredMatrixKeyword.value.trim()) return true
  const list = classificationMatrixGovernanceOrder.value
  const i = list.findIndex((r) => r.id === row.id)
  if (i <= 0) return true
  return !sameGovernancePriority(list[i], list[i - 1])
}

const isClassificationMatrixMoveDownDisabled = (row: DataSecureClassificationMatrix) => {
  if (structuredMatrixKeyword.value.trim()) return true
  const list = classificationMatrixGovernanceOrder.value
  const i = list.findIndex((r) => r.id === row.id)
  if (i < 0 || i >= list.length - 1) return true
  return !sameGovernancePriority(list[i], list[i + 1])
}

const moveClassificationMatrixUp = async (row: DataSecureClassificationMatrix) => {
  if (structuredMatrixKeyword.value.trim()) {
    ElMessage.warning('请先清空矩阵检索再调整顺序')
    return
  }
  const list = classificationMatrixGovernanceOrder.value
  const i = list.findIndex((r) => r.id === row.id)
  if (i <= 0) return
  const a = list[i - 1]
  const b = list[i]
  if (!sameGovernancePriority(a, b)) return
  const reason = await askChangeReason('调整显式分类矩阵顺序')
  if (!reason) return
  const sa = a.sort_order ?? 0
  const sb = b.sort_order ?? 0
  await toolsApi.updateDataSecureClassificationMatrix(props.toolId, {
    id: a.id,
    sort_order: sb,
    change_reason: reason
  })
  await toolsApi.updateDataSecureClassificationMatrix(props.toolId, {
    id: b.id,
    sort_order: sa,
    change_reason: reason
  })
  await loadStructuredGovernanceData()
}

const moveClassificationMatrixDown = async (row: DataSecureClassificationMatrix) => {
  if (structuredMatrixKeyword.value.trim()) {
    ElMessage.warning('请先清空矩阵检索再调整顺序')
    return
  }
  const list = classificationMatrixGovernanceOrder.value
  const i = list.findIndex((r) => r.id === row.id)
  if (i < 0 || i >= list.length - 1) return
  const a = list[i]
  const b = list[i + 1]
  if (!sameGovernancePriority(a, b)) return
  const reason = await askChangeReason('调整显式分类矩阵顺序')
  if (!reason) return
  const sa = a.sort_order ?? 0
  const sb = b.sort_order ?? 0
  await toolsApi.updateDataSecureClassificationMatrix(props.toolId, {
    id: a.id,
    sort_order: sb,
    change_reason: reason
  })
  await toolsApi.updateDataSecureClassificationMatrix(props.toolId, {
    id: b.id,
    sort_order: sa,
    change_reason: reason
  })
  await loadStructuredGovernanceData()
}

const submitStructuredSecurityCreate = async () => {
  if (!selectedSpaceId.value || secCreateForm.catalog_entry_id == null) {
    ElMessage.warning('请选择数据字段')
    return
  }
  const text = secCreateForm.requirement_text.trim()
  const expr = secCreateForm.logic_expression.trim()
  if (!text || !expr) {
    ElMessage.warning('请填写要求正文与逻辑表达式')
    return
  }
  if (!secRequirementExprValidation.value.valid) {
    ElMessage.warning(`表达式校验未通过：${secRequirementExprValidation.value.message}`)
    return
  }
  const pred: Record<string, unknown> = {}
  const seenTok = new Set<string>()
  for (const row of secPredRows.value) {
    const tok = (row.token || '').trim()
    if (!tok) {
      ElMessage.warning('请填写每一行的谓词标识，或删除空行')
      return
    }
    if (!/^[A-Za-z0-9_-]+$/.test(tok)) {
      ElMessage.warning(`谓词标识「${tok}」仅允许字母、数字、下划线与连字符`)
      return
    }
    if (seenTok.has(tok)) {
      ElMessage.warning(`谓词标识「${tok}」重复`)
      return
    }
    seenTok.add(tok)
    const val = (row.value || '').trim()
    if (!val) {
      ElMessage.warning(`请为谓词「${tok}」填写比较值`)
      return
    }
    if (row.kind === 'lifecycle_field_contains') {
      const fieldKey = (row.field_key || '').trim()
      if (!fieldKey) {
        ElMessage.warning(`请为谓词「${tok}」选择生命周期字段`)
        return
      }
      pred[tok] = { kind: row.kind, field_key: fieldKey, value: val }
    } else {
      pred[tok] = { kind: row.kind, value: val }
    }
  }
  if (!Object.keys(pred).length) {
    ElMessage.warning('请至少配置一行有效谓词')
    return
  }
  const changeReason = await askChangeReason('新增安全要求')
  if (!changeReason) return
  const prio = secCreateForm.priority ?? 0
  const catId = secCreateForm.catalog_entry_id
  const sameBand = structuredSecurityReqs.value.filter(
    (r) => r.catalog_entry_id === catId && (r.priority ?? 0) === prio
  )
  const maxSecSo = sameBand.reduce((m, r) => Math.max(m, r.sort_order ?? 0), -1)
  await toolsApi.createDataSecureFieldSecurityRequirement(props.toolId, {
    project_space_id: selectedSpaceId.value,
    catalog_entry_id: catId,
    requirement_text: text,
    logic_expression: expr,
    predicate_map: pred,
    priority: secCreateForm.priority,
    sort_order: maxSecSo + 1,
    change_reason: changeReason
  })
  ElMessage.success('已新增安全要求')
  secCreateForm.requirement_text = ''
  secCreateForm.logic_expression = ''
  secPredRows.value = [{ token: 'isC2', kind: 'grade_equals', value: 'C2-Confidential', field_key: '' }]
  await loadStructuredGovernanceData()
}

const runStructuredEval = async () => {
  if (!selectedSpaceId.value || structuredEvalCatalogId.value == null) return
  structuredEvalResult.value = await toolsApi.evalDataSecureFieldSecurityRequirements(props.toolId, {
    project_space_id: selectedSpaceId.value,
    catalog_entry_id: structuredEvalCatalogId.value
  })
}

watch(tab, (name) => {
  if (name === 'classification-governance' && selectedSpaceId.value) {
    void loadStructuredGovernanceData()
  } else if (name === 'change-logs' && selectedSpaceId.value) {
    void loadGovernanceChangeLogs()
  } else if (name === 'records') {
    void loadRecordsPaneData()
  } else if (name === 'questionnaire' && selectedSpaceId.value) {
    void loadQuestionnaireData()
  } else if (name === 'field-governance' && selectedSpaceId.value) {
    void loadFieldGovernanceData()
  }
})

watch(recordsInnerTab, () => {
  if (tab.value === 'records') {
    void loadRecordsPaneData()
  }
})

const onPageSizeChange = async (size: number) => {
  pageSize.value = size
  page.value = 1
  if (recordsInnerTab.value === 'submissions') {
    await loadAssessmentRows()
  }
}

const suggestKeyFromSource = async (source: string, target: DataSecureIdentifierKeyTarget): Promise<string> => {
  const t = source.trim()
  if (!t) return ''
  try {
    const { key } = await toolsApi.suggestDataSecureIdentifierKey(props.toolId, { source_text: t, target })
    return (key || '').trim()
  } catch {
    return ''
  }
}

const onSpaceKeyInput = () => {
  spaceKeyTouched.value = spaceForm.space_key.trim().length > 0
}
const onSpaceNameBlur = async () => {
  if (spaceKeyTouched.value) return
  const k = await suggestKeyFromSource(spaceForm.name, 'space_key')
  if (k) spaceForm.space_key = k
}

const onQuestionKeyInput = () => {
  questionKeyTouched.value = questionForm.question_key.trim().length > 0
}
const onQuestionTitleBlur = async () => {
  if (questionKeyTouched.value) return
  const k = await suggestKeyFromSource(questionForm.title, 'question_key')
  if (k) questionForm.question_key = k
}

const onLifecycleFieldKeyInput = () => {
  lifecycleFieldKeyTouched.value = newLifecycleField.field_key.trim().length > 0
}
const onLifecycleLabelBlur = async () => {
  if (lifecycleFieldKeyTouched.value) return
  const k = await suggestKeyFromSource(newLifecycleField.label, 'lifecycle_field_key')
  if (k) newLifecycleField.field_key = k
}

const onTaxonomyNodeKeyInput = () => {
  taxonomyNodeKeyTouched.value = taxCreateForm.node_key.trim().length > 0
}
const onTaxonomyNameBlur = async () => {
  if (taxonomyNodeKeyTouched.value) return
  const k = await suggestKeyFromSource(taxCreateForm.name, 'taxonomy_node_key')
  if (k) taxCreateForm.node_key = k
}

const createSpace = async () => {
  if (!spaceForm.name.trim()) return ElMessage.warning('请填写空间名称')
  let sk = spaceForm.space_key.trim()
  if (!sk) {
    sk = await suggestKeyFromSource(spaceForm.name, 'space_key')
    spaceForm.space_key = sk
  }
  if (!sk) return ElMessage.warning('无法生成空间标识，请检查空间名称或手动填写')
  let changeReason: string | undefined
  if (spaceForm.copy_from_project_space_id != null) {
    const src = spaces.value.find((s) => s.id === spaceForm.copy_from_project_space_id)
    const label = src ? `「${src.name}」` : '所选空间'
    const r = await askChangeReason(`从${label}复制配置到新项目空间`)
    if (r == null) return
    changeReason = r
  }
  const payload: Parameters<typeof toolsApi.createDataSecureProjectSpace>[1] = {
    space_key: sk,
    name: spaceForm.name.trim(),
    description: spaceForm.description.trim() || undefined,
    is_active: true
  }
  if (spaceForm.copy_from_project_space_id != null) {
    payload.copy_from_project_space_id = spaceForm.copy_from_project_space_id
    payload.change_reason = changeReason
  }
  await toolsApi.createDataSecureProjectSpace(props.toolId, payload)
  ElMessage.success(spaceForm.copy_from_project_space_id != null ? '项目空间已新增并已复制配置' : '项目空间已新增')
  Object.assign(spaceForm, { space_key: '', name: '', description: '', copy_from_project_space_id: null })
  spaceKeyTouched.value = false
  await loadSpaces()
}

const confirmDeleteSpace = async (row: DataSecureProjectSpace) => {
  try {
    await ElMessageBox.confirm(
      `将永久删除项目空间「${row.name}」及其中的问卷、主表、填报、分类与审计等全部数据，不可恢复。是否继续？`,
      '删除项目空间',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' }
    )
  } catch {
    return
  }
  const changeReason = await askChangeReason(`删除项目空间「${row.name}」`)
  if (changeReason == null) return
  await toolsApi.deleteDataSecureProjectSpace(props.toolId, { id: row.id, change_reason: changeReason })
  ElMessage.success('项目空间已删除')
  await loadSpaces()
}

const toggleSpace = async (row: DataSecureProjectSpace) => {
  await toolsApi.updateDataSecureProjectSpace(props.toolId, { id: row.id, is_active: !row.is_active })
  ElMessage.success('项目空间状态已更新')
  await loadSpaces()
}
const createQuestion = async () => {
  if (!selectedSpaceId.value) return ElMessage.warning('请先选择项目空间')
  if (!questionForm.title.trim()) return ElMessage.warning('请填写题目标题')
  let qk = questionForm.question_key.trim()
  if (!qk) {
    qk = await suggestKeyFromSource(questionForm.title, 'question_key')
    questionForm.question_key = qk
  }
  if (!qk) return ElMessage.warning('无法生成题目标识，请检查标题或手动填写')
  const maxSo = questions.value.reduce((m, q) => Math.max(m, q.sort_order ?? 0), -1)
  await toolsApi.createDataSecureQuestion(props.toolId, {
    project_space_id: selectedSpaceId.value,
    question_key: qk,
    title: questionForm.title,
    help_text: questionForm.help_text.trim() || undefined,
    sort_order: maxSo + 1
  })
  ElMessage.success('问卷题目已新增')
  Object.assign(questionForm, { question_key: '', title: '', help_text: '' })
  questionKeyTouched.value = false
  await loadQuestionnaireData()
}

const createQuestionBatch = async () => {
  if (!selectedSpaceId.value) return ElMessage.warning('请先选择项目空间')
  const lines = (questionBatchText.value || '')
    .split(/\r?\n/)
    .map((x) => x.trim())
    .filter(Boolean)
  if (!lines.length) return ElMessage.warning('请先填写批量新增内容')
  let ok = 0
  const errs: string[] = []
  let nextSort = questions.value.reduce((m, q) => Math.max(m, q.sort_order ?? 0), -1) + 1
  for (const line of lines) {
    let questionKey = ''
    let title = ''
    if (!line.includes(',')) {
      title = line.trim()
    } else {
      const [a, ...rest] = line.split(',')
      const b = rest.join(',').trim()
      const left = (a || '').trim()
      if (left && b) {
        questionKey = left
        title = b
      } else if (!left && b) {
        title = b
      } else {
        errs.push(`格式错误：${line}`)
        continue
      }
    }
    if (!title) {
      errs.push(`格式错误：${line}`)
      continue
    }
    if (!questionKey) {
      questionKey = await suggestKeyFromSource(title, 'question_key')
    }
    if (!questionKey) {
      errs.push(`无法生成题目标识：${line}`)
      continue
    }
    try {
      await toolsApi.createDataSecureQuestion(props.toolId, {
        project_space_id: selectedSpaceId.value,
        question_key: questionKey,
        title,
        sort_order: nextSort
      })
      nextSort += 1
      ok += 1
    } catch (e: any) {
      errs.push(`${questionKey}: ${e?.message || '新增失败'}`)
    }
  }
  if (ok) ElMessage.success(`批量新增题目成功 ${ok} 条`)
  if (errs.length) {
    await ElMessageBox.alert(errs.slice(0, 30).join('\n'), '部分题目新增失败', { type: 'warning' })
  }
  questionBatchText.value = ''
  await loadQuestionnaireData()
}
const openQuestionHelpDialog = (row: DataSecureQuestion) => {
  questionHelpEdit.value = { id: row.id, title: row.title, help_text: row.help_text || '' }
  questionHelpDialogVisible.value = true
}
const onQuestionHelpDialogClosed = () => {
  questionHelpEdit.value = null
}
const saveQuestionHelp = async () => {
  if (!questionHelpEdit.value) return
  questionHelpSaving.value = true
  try {
    await toolsApi.updateDataSecureQuestion(props.toolId, {
      id: questionHelpEdit.value.id,
      help_text: questionHelpEdit.value.help_text.trim() || null
    })
    ElMessage.success('问题说明已保存')
    questionHelpDialogVisible.value = false
    await loadQuestionnaireData()
  } catch (error: any) {
    ElMessage.error(error?.message || '保存失败')
  } finally {
    questionHelpSaving.value = false
  }
}
const toggleQuestion = async (row: DataSecureQuestion) => {
  await toolsApi.updateDataSecureQuestion(props.toolId, { id: row.id, is_active: !row.is_active })
  ElMessage.success('题目状态已更新')
  await loadQuestionnaireData()
}
const confirmDeleteQuestion = async (row: DataSecureQuestion) => {
  try {
    await ElMessageBox.confirm(
      `确定删除题目「${row.title}」？删除后不可恢复。`,
      '删除题目',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' }
    )
  } catch {
    return
  }
  const changeReason = await askChangeReason(`删除问卷题目「${row.title}」`)
  if (changeReason == null) return
  await toolsApi.deleteDataSecureQuestion(props.toolId, { id: row.id, change_reason: changeReason })
  ElMessage.success('题目已删除')
  await loadQuestionnaireData()
}
const saveRule = async () => {
  if (!selectedSpaceId.value) return ElMessage.warning('请先选择项目空间')
  if (!ruleForm.logic_expression.trim()) {
    return ElMessage.warning('请填写逻辑表达式')
  }
  if (!expressionValidation.value.valid) {
    return ElMessage.warning(`表达式校验未通过：${expressionValidation.value.message}`)
  }
  const changeReason = await askChangeReason('保存相关性判定规则')
  if (!changeReason) return
  await toolsApi.upsertDataSecureRelevanceRule(props.toolId, {
    project_space_id: selectedSpaceId.value,
    min_yes_count: ruleForm.min_yes_count,
    logic_operator: ruleForm.logic_operator,
    question_keys: ruleForm.question_keys,
    logic_expression: ruleForm.logic_expression,
    notes: ruleForm.notes,
    change_reason: changeReason
  })
  ElMessage.success('判定规则已保存')
}
const appendExpressionToken = (token: string) => {
  const current = ruleForm.logic_expression || ''
  const needsSpace = current.length > 0 && !current.endsWith(' ') && !token.startsWith(' ') && token !== ')' && token !== '('
  ruleForm.logic_expression = `${current}${needsSpace ? ' ' : ''}${token}`.trimStart()
}
const clearExpression = () => {
  ruleForm.logic_expression = ''
}

const createLifecycleField = async () => {
  if (!selectedSpaceId.value) {
    ElMessage.warning('请先选择项目空间')
    return
  }
  if (!newLifecycleField.label.trim()) {
    ElMessage.warning('请填写字段名称')
    return
  }
  let key = newLifecycleField.field_key.trim()
  if (!key) {
    key = await suggestKeyFromSource(newLifecycleField.label, 'lifecycle_field_key')
    newLifecycleField.field_key = key
  }
  if (!key) {
    ElMessage.warning('无法生成字段 Key，请检查字段名称或手动填写')
    return
  }
  if (!FIELD_KEY_PATTERN.test(key)) {
    ElMessage.warning('字段 Key 须以小写字母开头，且仅含小写字母、数字、下划线')
    return
  }
  const changeReason = await askChangeReason(`新增字段 ${key}`)
  if (!changeReason) return
  lifecycleCreating.value = true
  try {
    await toolsApi.createDataSecureLifecycleFieldConfig(props.toolId, {
      project_space_id: selectedSpaceId.value,
      field_key: key,
      label: newLifecycleField.label.trim(),
      input_type: newLifecycleField.input_type,
      change_reason: changeReason
    })
    Object.assign(newLifecycleField, { field_key: '', label: '', input_type: 'text' as FormFieldInputType })
    lifecycleFieldKeyTouched.value = false
    ElMessage.success('数据生命周期字段已新增')
    await loadLifecycleFieldConfigs()
  } catch (error: any) {
    const base = error?.message || '新增字段失败'
    if (error?.status === 403) {
      ElMessage.error(`${base}。若您不是该工具在系统中的负责人，请联系管理员将您设为工具负责人。`)
    } else {
      ElMessage.error(base)
    }
  } finally {
    lifecycleCreating.value = false
  }
}

const createLifecycleFieldBatch = async () => {
  if (!selectedSpaceId.value) return ElMessage.warning('请先选择项目空间')
  const lines = (lifecycleBatchText.value || '')
    .split(/\r?\n/)
    .map((x) => x.trim())
    .filter(Boolean)
  if (!lines.length) return ElMessage.warning('请先填写批量新增内容')
  const changeReason = await askChangeReason(`批量新增生命周期字段（${lines.length}条）`)
  if (!changeReason) return
  let ok = 0
  const errs: string[] = []
  const validIt = (s: string): s is FormFieldInputType =>
    ['text', 'textarea', 'single_select', 'multi_select'].includes(s)

  for (const line of lines) {
    const parts = line.split(',').map((x) => (x || '').trim())
    let fieldKey = ''
    let label = ''
    let inputType: FormFieldInputType = 'text'
    if (parts.length >= 3) {
      fieldKey = parts[0]
      label = parts[1]
      inputType = (parts[2] || 'text') as FormFieldInputType
    } else if (parts.length === 2) {
      const [a, b] = parts
      if (FIELD_KEY_PATTERN.test(a)) {
        fieldKey = a
        label = b
        inputType = 'text'
      } else if (validIt(b)) {
        label = a
        inputType = b
      } else {
        label = `${a},${b}`
      }
    } else if (parts.length === 1) {
      label = parts[0] || ''
    } else {
      errs.push(`格式错误：${line}`)
      continue
    }
    if (!label) {
      errs.push(`格式错误：${line}`)
      continue
    }
    if (!fieldKey) {
      fieldKey = await suggestKeyFromSource(label, 'lifecycle_field_key')
    }
    if (!fieldKey) {
      errs.push(`无法生成字段 key：${line}`)
      continue
    }
    if (!FIELD_KEY_PATTERN.test(fieldKey)) {
      errs.push(`${fieldKey}: 字段 key 不合法`)
      continue
    }
    if (!['text', 'textarea', 'single_select', 'multi_select'].includes(inputType)) {
      errs.push(`${fieldKey}: input_type 仅支持 text/textarea/single_select/multi_select`)
      continue
    }
    try {
      await toolsApi.createDataSecureLifecycleFieldConfig(props.toolId, {
        project_space_id: selectedSpaceId.value,
        field_key: fieldKey,
        label,
        input_type: inputType,
        change_reason: changeReason
      })
      ok += 1
    } catch (e: any) {
      errs.push(`${fieldKey}: ${e?.message || '新增失败'}`)
    }
  }
  if (ok) ElMessage.success(`批量新增字段成功 ${ok} 条`)
  if (errs.length) {
    await ElMessageBox.alert(errs.slice(0, 30).join('\n'), '部分字段新增失败', { type: 'warning' })
  }
  lifecycleBatchText.value = ''
  await loadLifecycleFieldConfigs()
}
const saveLifecycleFields = async () => {
  if (!selectedSpaceId.value) return ElMessage.warning('请先选择项目空间')
  const changeReason = await askChangeReason('保存数据生命周期字段配置')
  if (!changeReason) return
  lifecycleSaving.value = true
  try {
    await toolsApi.updateDataSecureLifecycleFieldConfigs(props.toolId, {
      project_space_id: selectedSpaceId.value,
      items: lifecycleFieldRows.value.map((row) => ({
        field_key: row.field_key,
        label: row.label,
        input_type: row.input_type,
        sort_order: row.sort_order,
        help_text: row.help_text || null,
        required: row.required,
        min_length: row.min_length ?? null,
        max_length: row.max_length ?? null,
        regex_pattern: row.regex_pattern || null,
        regex_error_message: row.regex_error_message || null,
        allowed_values: row.allowed_values_text
          .split(',')
          .map((s) => s.trim())
          .filter(Boolean),
      })),
      change_reason: changeReason
    })
    ElMessage.success('数据生命周期字段配置已保存')
    await loadLifecycleFieldConfigs()
  } finally {
    lifecycleSaving.value = false
  }
}
const deleteLifecycleField = async (row: FieldConfigTableRow) => {
  if (!selectedSpaceId.value) return
  if (row.is_builtin) {
    ElMessage.warning('内置字段不可删除')
    return
  }
  const changeReason = await askChangeReason(`删除字段 ${row.field_key}`)
  if (!changeReason) return
  await toolsApi.deleteDataSecureLifecycleFieldConfig(props.toolId, {
    project_space_id: selectedSpaceId.value,
    field_key: row.field_key,
    change_reason: changeReason
  })
  ElMessage.success('字段已删除')
  await loadLifecycleFieldConfigs()
}
const reviewFieldRequest = async (requestId: number, status: 'approved' | 'rejected') => {
  await toolsApi.reviewDataSecureFieldRequest(props.toolId, requestId, {
    status,
    review_notes: status === 'approved' ? '通过字段治理审核' : '本次申请未通过，请补充信息后重提'
  })
  ElMessage.success(status === 'approved' ? '已通过申请' : '已驳回申请')
  await loadFieldRequests()
  await loadFieldCatalog()
}

const reviewBfOptionRequest = async (requestId: number, status: 'approved' | 'rejected') => {
  try {
    await toolsApi.reviewDataSecureBusinessFunctionOptionRequest(props.toolId, requestId, {
      status,
      review_notes: status === 'approved' ? '已通过，选项已写入业务功能允许值' : '本次申请未通过'
    })
    ElMessage.success(status === 'approved' ? '已通过申请' : '已驳回申请')
    await loadBfOptionRequests()
    await loadLifecycleFieldConfigs()
  } catch (e: any) {
    ElMessage.error(e?.message || '审核失败')
  }
}

const onCatalogExtraDialogClosed = () => {
  catalogExtraEditEntry.value = null
  catalogExtraForm.value = {}
}

const openCatalogExtraEdit = (row: DataSecureFieldCatalogEntry) => {
  catalogExtraEditEntry.value = row
  catalogExtraForm.value = { ...(row.extra_fields || {}) }
  catalogExtraDialogVisible.value = true
}

const saveCatalogExtraFields = async () => {
  const entry = catalogExtraEditEntry.value
  if (!entry) return
  catalogExtraSaving.value = true
  try {
    await toolsApi.updateDataSecureFieldCatalogExtra(props.toolId, entry.id, {
      extra_fields: { ...catalogExtraForm.value }
    })
    ElMessage.success('其他信息已保存')
    catalogExtraDialogVisible.value = false
    await loadFieldCatalog()
  } catch (error: any) {
    ElMessage.error(error?.message || '保存其他信息失败')
  } finally {
    catalogExtraSaving.value = false
  }
}

const splitCsvLine = (line: string): string[] => {
  const out: string[] = []
  let cell = ''
  let inQ = false
  for (let i = 0; i < line.length; i++) {
    const c = line[i]
    if (c === '"') {
      if (inQ && line[i + 1] === '"') {
        cell += '"'
        i++
      } else {
        inQ = !inQ
      }
    } else if (!inQ && c === ',') {
      out.push(cell.trim())
      cell = ''
    } else {
      cell += c
    }
  }
  out.push(cell.trim())
  return out
}

const parseMatrixFromCsvText = (text: string): string[][] => {
  const normalized = text.replace(/^\uFEFF/, '')
  const rawLines = normalized.split(/\r?\n/).filter((ln) => ln.trim().length > 0)
  return rawLines.map((ln) => splitCsvLine(ln))
}

const escapeCsvCell = (value: string): string => {
  const s = String(value ?? '')
  if (/[",\n\r]/.test(s)) return `"${s.replace(/"/g, '""')}"`
  return s
}

/** CSV 表头：支持中文或英文别名，大小写不敏感（英文） */
const matchCsvHeaderColumn = (headers: string[], aliases: string[]): number => {
  const trimmed = headers.map((h) => h.replace(/^\uFEFF/, '').trim())
  for (const alias of aliases) {
    const want = alias.trim()
    const i = trimmed.findIndex((h) => h === want || h.toLowerCase() === want.toLowerCase())
    if (i >= 0) return i
  }
  return -1
}

/** 与后端 data_secure_dynamic_fields.FIELD_KEY_PATTERN 一致 */
const CATALOG_CSV_FIELD_KEY_PATTERN = /^[a-z][a-z0-9_]{0,63}$/

const stableImportFieldKeyFromHeader = (header: string, columnIndex: number): string => {
  const t = header.trim()
  let h = (2166136261 ^ columnIndex) >>> 0
  for (let i = 0; i < t.length; i++) {
    h = Math.imul(h ^ t.charCodeAt(i), 16777619) >>> 0
  }
  const hex = h.toString(16).padStart(8, '0')
  const h2 = Math.imul(h, 31 + columnIndex) >>> 0
  const hex2 = h2.toString(16).padStart(8, '0')
  return `i_${(hex + hex2).slice(0, 12)}`
}

const catalogImportDisplayLabel = (headerCell: string, fieldKey: string): string => {
  const t = headerCell.trim()
  const bracket = t.match(/^(.+?)\[([a-z][a-z0-9_]*)]\s*$/i)
  if (bracket?.[1]) {
    const namePart = bracket[1].trim()
    if (namePart) return namePart
  }
  return t || fieldKey
}

const buildCatalogImportItems = (
  matrix: string[][]
): { items: Array<{ field_name: string; extra_fields: Record<string, any> }>; auto_field_labels: Record<string, string> } => {
  if (matrix.length < 2) return { items: [], auto_field_labels: {} }
  const headers = matrix[0].map((h) => h.replace(/^\uFEFF/, '').trim())
  const fieldIdx = matchCsvHeaderColumn(headers, ['数据字段', 'field_name', '数据字段名称'])
  if (fieldIdx < 0) return { items: [], auto_field_labels: {} }
  const preExistingCustomKeys = new Set(lifecycleDynamicFieldsForCatalogEdit.value.map((f) => f.field_key))
  const resolveExtraHeaderToFieldKey = (headerCell: string, columnIndex: number): string | null => {
    const t = headerCell.trim()
    if (!t) return null
    const bracket = t.match(/^(.+?)\[([a-z][a-z0-9_]*)]\s*$/i)
    if (bracket?.[2]) {
      const k = bracket[2].toLowerCase()
      if (CATALOG_CSV_FIELD_KEY_PATTERN.test(k)) return k
      return stableImportFieldKeyFromHeader(headerCell, columnIndex)
    }
    if (preExistingCustomKeys.has(t)) return t
    const byLabel = lifecycleFields.value.find((f) => !f.is_builtin && f.label === t)
    if (byLabel) return byLabel.field_key
    if (CATALOG_CSV_FIELD_KEY_PATTERN.test(t)) return t
    return stableImportFieldKeyFromHeader(headerCell, columnIndex)
  }
  const auto_field_labels: Record<string, string> = {}
  const items: Array<{ field_name: string; extra_fields: Record<string, any> }> = []
  for (let r = 1; r < matrix.length; r++) {
    const row = matrix[r]
    if (!row.length) continue
    const fn = (row[fieldIdx] ?? '').trim()
    if (!fn) continue
    const extra: Record<string, any> = {}
    headers.forEach((h, j) => {
      if (j === fieldIdx) return
      const hk = resolveExtraHeaderToFieldKey(h, j)
      if (!hk) return
      const raw = (row[j] ?? '').trim()
      if (!raw) return
      if (!preExistingCustomKeys.has(hk) && auto_field_labels[hk] === undefined) {
        auto_field_labels[hk] = catalogImportDisplayLabel(h, hk).slice(0, 100)
      }
      const def = lifecycleFields.value.find((f) => f.field_key === hk)
      if (def?.input_type === 'multi_select') {
        extra[hk] = raw.split(/[;；]/).map((s) => s.trim()).filter(Boolean)
      } else {
        extra[hk] = raw
      }
    })
    items.push({ field_name: fn, extra_fields: extra })
  }
  return { items, auto_field_labels }
}

const onManualCatalogDialogClosed = () => {
  manualCatalogFieldName.value = ''
  manualCatalogExtraFields.value = {}
}

const openManualCatalogCreate = () => {
  if (!selectedSpaceId.value) {
    ElMessage.warning('请先选择项目空间')
    return
  }
  manualCatalogFieldName.value = ''
  manualCatalogExtraFields.value = {}
  manualCatalogDialogVisible.value = true
}

const submitManualCatalogCreate = async () => {
  if (!selectedSpaceId.value) {
    ElMessage.warning('请先选择项目空间')
    return
  }
  const name = manualCatalogFieldName.value.trim()
  if (!name) {
    ElMessage.warning('请填写数据字段名称')
    return
  }
  manualCatalogSaving.value = true
  try {
    await toolsApi.createDataSecureFieldCatalogEntry(props.toolId, {
      project_space_id: selectedSpaceId.value,
      field_name: name,
      extra_fields: { ...manualCatalogExtraFields.value }
    })
    ElMessage.success('主表记录已新增')
    manualCatalogDialogVisible.value = false
    await loadFieldCatalog()
  } catch (error: any) {
    ElMessage.error(error?.message || '新增失败')
  } finally {
    manualCatalogSaving.value = false
  }
}

const downloadCatalogCsvTemplate = () => {
  if (!selectedSpaceId.value) {
    ElMessage.warning('请先选择项目空间')
    return
  }
  const dyn = lifecycleDynamicFieldsForCatalogEdit.value
  const headerCells = ['数据字段', ...dyn.map((f) => `${f.label}[${f.field_key}]`)]
  const header = headerCells.map(escapeCsvCell).join(',')
  const blob = new Blob([`\uFEFF${header}\n`], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = '数据字段主表-导入模板.csv'
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
  ElMessage.success('已下载模板：首列为数据字段，其余列推荐「列名[field_key]」；未事先配置的列也可在导入时自动建为单行文本字段（须补全限制配置）')
}

const triggerCatalogCsvImport = () => {
  if (!selectedSpaceId.value) {
    ElMessage.warning('请先选择项目空间')
    return
  }
  catalogCsvInputRef.value?.click()
}

const onCatalogCsvFileChange = async (ev: Event) => {
  const target = ev.target as HTMLInputElement
  const file = target.files?.[0]
  target.value = ''
  if (!file) return
  if (!selectedSpaceId.value) {
    ElMessage.warning('请先选择项目空间')
    return
  }
  try {
    const text = await file.text()
    const matrix = parseMatrixFromCsvText(text)
    if (matrix.length < 2) {
      ElMessage.warning('CSV 至少需要一行表头与一行数据')
      return
    }
    const { items, auto_field_labels } = buildCatalogImportItems(matrix)
    if (!items.length) {
      ElMessage.warning('未解析到有效数据：请确认首列表头为「数据字段」或 field_name，且数据行首列不为空')
      return
    }
    const limited = items.slice(0, 500)
    if (items.length > 500) {
      ElMessage.warning(`共 ${items.length} 条，仅提交前 500 条`)
    }
    const res = await toolsApi.batchImportDataSecureFieldCatalog(props.toolId, {
      project_space_id: selectedSpaceId.value,
      items: limited,
      auto_field_labels: Object.keys(auto_field_labels).length ? auto_field_labels : undefined
    })
    const parts = [
      `新增 ${res.created_count} 条`,
      `跳过重复 ${res.skipped_duplicate} 条`,
      res.failed_validation ? `校验失败 ${res.failed_validation} 条` : ''
    ].filter(Boolean)
    ElMessage.success(parts.join('，'))
    if (res.errors.length) {
      await ElMessageBox.alert(res.errors.join('\n'), '未导入行说明', { type: 'warning' })
    }
    const autoKeys = res.auto_created_field_keys ?? []
    if (autoKeys.length) {
      await loadLifecycleFieldConfigs()
      const keysText = autoKeys.join('、')
      await ElMessageBox.alert(
        `根据 CSV 表头已自动新建数据生命周期字段（单行文本、未做必填/长度/选项等限制）：${keysText}。\n\n请工具负责人打开「字段与主表 → 数据生命周期字段」，为上述字段补充校验与展示配置。`,
        '导入提示',
        { type: 'warning' }
      )
    }
    await loadFieldCatalog()
  } catch (error: any) {
    ElMessage.error(error?.message || '导入失败')
  }
}

const downloadBlobCsv = (filename: string, lines: string[]) => {
  const blob = new Blob([`\uFEFF${lines.join('\n')}\n`], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
}

const downloadGovernanceTaxonomyTemplate = () => {
  const header = ['上级节点标识', '节点名称', '节点标识', '排序'].map(escapeCsvCell).join(',')
  const sample = [
    ['', '用户数据', 'userdata', '0'].map(escapeCsvCell).join(','),
    ['userdata', '联系方式', 'contact', '10'].map(escapeCsvCell).join(','),
    ['contact', '手机号', 'phone', '20'].map(escapeCsvCell).join(',')
  ]
  downloadBlobCsv('分类分级-分类树模板.csv', [header, ...sample])
  ElMessage.success('已下载分类树 CSV 模板（中文表头；仍兼容旧版英文表头导入）')
}

const downloadGovernanceClassGradeTemplate = () => {
  const header = ['数据字段', '一级分类标识', '二级分类标识', '最细分类标识', '密级', '备注'].map(escapeCsvCell).join(',')
  const sample1 = ['user_id', 'userdata', 'contact', '', 'C2-Confidential', '兼容旧模板：可只填前两列'].map(escapeCsvCell).join(',')
  const sample2 = ['order_id', '', '', 'phone', 'C1-Internal', '仅用「最细」一列时前两列可空'].map(escapeCsvCell).join(',')
  downloadBlobCsv('分类分级-密级绑定模板.csv', [header, sample1, sample2])
  ElMessage.success('已下载密级绑定 CSV 模板')
}

const downloadGovernanceSecurityTemplate = () => {
  const header = ['数据字段', '要求摘要', '逻辑表达式', '谓词JSON', '优先级', '排序'].map(escapeCsvCell).join(',')
  const pred = JSON.stringify({ isC2: { kind: 'grade_equals', value: 'C2-Confidential' } })
  const sampleRow = ['user_id', '须脱敏展示', 'isC2', pred, '100', '0'].map(escapeCsvCell).join(',')
  downloadBlobCsv('分类分级-安全要求模板.csv', [header, sampleRow])
  ElMessage.success('已下载安全要求 CSV 模板')
}

const triggerGovernanceTaxonomyCsv = () => governanceTaxonomyCsvInputRef.value?.click()
const triggerGovernanceClassGradeCsv = () => governanceClassGradeCsvInputRef.value?.click()
const triggerGovernanceSecurityCsv = () => governanceSecurityCsvInputRef.value?.click()
const triggerConfigJsonImport = () => configJsonInputRef.value?.click()

const defaultConfigExportSelection = (): DataSecureConfigExportSelection => ({
  include_spaces: true,
  include_questions: true,
  include_relevance_rule: true,
  include_lifecycle_fields: true,
  include_taxonomy_nodes: true,
  include_field_class_grades: true,
  include_security_requirements: true,
  include_classification_rules: true,
  include_classification_matrix: true
})

const downloadJsonFile = (filename: string, payload: unknown) => {
  const text = JSON.stringify(payload, null, 2)
  const blob = new Blob([text], { type: 'application/json;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
}

const exportConfigBundle = async () => {
  if (!selectedSpaceId.value) return ElMessage.warning('请先选择项目空间')
  const res = await toolsApi.exportDataSecureConfig(props.toolId, {
    project_space_id: selectedSpaceId.value,
    selection: defaultConfigExportSelection()
  })
  downloadJsonFile(`数据安全治理配置-空间${selectedSpaceId.value}.json`, res)
  ElMessage.success('配置 JSON 已导出')
}

const onConfigJsonFileChange = async (ev: Event) => {
  const target = ev.target as HTMLInputElement
  const file = target.files?.[0]
  target.value = ''
  if (!file || !selectedSpaceId.value) return
  try {
    const text = await file.text()
    const payload = JSON.parse(text) as DataSecureConfigExportPayload
    if (!payload?.tool_key || payload.tool_key !== 'data-secure-manage') {
      ElMessage.warning('配置文件不属于数据安全治理工具')
      return
    }
    const changeReason = await askChangeReason('导入配置JSON')
    if (!changeReason) return
    const result = await toolsApi.importDataSecureConfig(props.toolId, {
      target_project_space_id: selectedSpaceId.value,
      payload,
      change_reason: changeReason
    })
    const detail = Object.entries(result.imported_counts || {})
      .map(([k, v]) => `${k}:${v}`)
      .join('，')
    ElMessage.success(detail ? `导入完成（${detail}）` : '导入完成')
    await loadQuestionnaireData()
    await loadFieldGovernanceData()
    await loadStructuredGovernanceData()
    await loadGovernanceChangeLogs()
  } catch (error: any) {
    ElMessage.error(error?.message || '导入配置失败')
  }
}

const submitBatchDeleteConfigs = async () => {
  if (!selectedSpaceId.value) return
  let itemsRaw: Array<{ domain: DataSecureConfigDeleteDomain; target_id: string }> = []
  try {
    itemsRaw = JSON.parse(batchDeleteJsonText.value || '[]')
  } catch {
    ElMessage.warning('删除配置 JSON 格式错误')
    return
  }
  if (!Array.isArray(itemsRaw) || !itemsRaw.length) {
    ElMessage.warning('请填写待删除配置列表')
    return
  }
  const allowed = new Set(['question', 'lifecycle_field', 'taxonomy_node', 'field_class_grade', 'security_requirement'])
  const items = itemsRaw
    .map((it) => ({ domain: String(it.domain) as DataSecureConfigDeleteDomain, target_id: String(it.target_id || '').trim() }))
    .filter((it) => allowed.has(it.domain) && it.target_id)
  if (!items.length) {
    ElMessage.warning('未识别到有效删除项')
    return
  }
  const changeReason = await askChangeReason(`批量删除配置（${items.length}条）`)
  if (!changeReason) return
  const res = await toolsApi.batchDeleteDataSecureConfig(props.toolId, {
    project_space_id: selectedSpaceId.value,
    change_reason: changeReason,
    items
  })
  if ((res.failed_items || []).length) {
    await ElMessageBox.alert((res.failed_items || []).map((x: any) => `${x.domain}:${x.target_id} -> ${x.reason || '失败'}`).join('\n'), '部分删除失败', {
      type: 'warning'
    })
  }
  ElMessage.success(`已删除 ${res.deleted_count} 条配置`)
  batchDeleteJsonText.value = ''
  await loadQuestionnaireData()
  await loadFieldGovernanceData()
  await loadStructuredGovernanceData()
  await loadGovernanceChangeLogs()
}

/** 分类树：与 CSV 文件导入相同解析规则（matrix 含表头行） */
const importGovernanceTaxonomyMatrix = async (matrix: string[][], changeReason: string) => {
  if (!selectedSpaceId.value) return
  if (matrix.length < 2) {
    ElMessage.warning('CSV 至少需要一行表头与一行数据')
    return
  }
  const headers = matrix[0].map((h) => h.replace(/^\uFEFF/, '').trim())
  const iParent = matchCsvHeaderColumn(headers, ['上级节点标识', '父节点标识', 'parent_node_key'])
  const iName = matchCsvHeaderColumn(headers, ['节点名称', 'name'])
  const iKey = matchCsvHeaderColumn(headers, ['节点标识', 'node_key'])
  const iSort = matchCsvHeaderColumn(headers, ['排序', 'sort_order'])
  if (iName < 0 || iKey < 0) {
    ElMessage.warning('表头须包含「节点名称」「节点标识」（或英文 name、node_key），可选「上级节点标识」「排序」')
    return
  }
  await loadStructuredGovernanceData()
  const keyToId: Record<string, number> = {}
  for (const n of taxonomyNodesAll.value) {
    if (n.is_active) keyToId[n.node_key] = n.id
  }
  const rows = matrix.slice(1).filter((r) => (r[iKey] || '').trim())
  const parentCell = (r: string[]) => (iParent >= 0 ? (r[iParent] || '').trim() : '')
  const pending = [...rows]
  let ok = 0
  const errs: string[] = []
  let guard = 0
  while (pending.length && guard < 5000) {
    guard += 1
    let progressed = false
    for (let i = pending.length - 1; i >= 0; i -= 1) {
      const r = pending[i]
      const nk = (r[iKey] || '').trim()
      if (keyToId[nk]) {
        pending.splice(i, 1)
        continue
      }
      const pk = parentCell(r)
      if (!pk) {
        try {
          const created = await toolsApi.createDataSecureTaxonomyNode(props.toolId, {
            project_space_id: selectedSpaceId.value,
            name: (r[iName] || '').trim() || nk,
            node_key: nk,
            sort_order: iSort >= 0 ? Number(r[iSort]) || 0 : 0,
            change_reason: changeReason
          })
          keyToId[nk] = created.id
          ok += 1
          progressed = true
          pending.splice(i, 1)
        } catch (e: any) {
          errs.push(`${nk}: ${e?.message || '失败'}`)
          pending.splice(i, 1)
        }
        continue
      }
      const pid = keyToId[pk]
      if (!pid) continue
      try {
        const created = await toolsApi.createDataSecureTaxonomyNode(props.toolId, {
          project_space_id: selectedSpaceId.value,
          parent_id: pid,
          name: (r[iName] || '').trim() || nk,
          node_key: nk,
          sort_order: iSort >= 0 ? Number(r[iSort]) || 0 : 0,
          change_reason: changeReason
        })
        keyToId[nk] = created.id
        ok += 1
        progressed = true
        pending.splice(i, 1)
      } catch (e: any) {
        errs.push(`${nk}: ${e?.message || '失败'}`)
        pending.splice(i, 1)
      }
    }
    if (!progressed) break
  }
  for (const r of pending) {
    const nk = (r[iKey] || '').trim()
    const pk = parentCell(r)
    errs.push(`${nk}: 无法导入（上级「${pk || '（根）'}」未就绪或存在循环引用）`)
  }
  ElMessage.success(`分类树导入完成：成功 ${ok} 条`)
  if (errs.length) await ElMessageBox.alert(errs.slice(0, 30).join('\n'), '部分行未导入', { type: 'warning' })
  await loadStructuredGovernanceData()
}

const onGovernanceTaxonomyCsvChange = async (ev: Event) => {
  const target = ev.target as HTMLInputElement
  const file = target.files?.[0]
  target.value = ''
  if (!file || !selectedSpaceId.value) return
  const changeReason = await askChangeReason('分类树 CSV 导入')
  if (!changeReason) return
  try {
    const text = await file.text()
    const matrix = parseMatrixFromCsvText(text)
    await importGovernanceTaxonomyMatrix(matrix, changeReason)
  } catch (error: any) {
    ElMessage.error(error?.message || '导入失败')
  }
}

const applyGovernanceTaxonomyBatchText = async () => {
  if (!selectedSpaceId.value) return ElMessage.warning('请先选择项目空间')
  const matrix = parseMatrixFromCsvText(governanceTaxonomyBatchText.value)
  if (matrix.length < 2) {
    ElMessage.warning('至少需要一行表头与一行数据')
    return
  }
  const changeReason = await askChangeReason('分类树 文本批量导入')
  if (!changeReason) return
  try {
    await importGovernanceTaxonomyMatrix(matrix, changeReason)
    governanceTaxonomyBatchText.value = ''
  } catch (error: any) {
    ElMessage.error(error?.message || '导入失败')
  }
}

const importGovernanceClassGradeMatrix = async (matrix: string[][], changeReason: string) => {
  if (!selectedSpaceId.value) return
  if (matrix.length < 2) {
    ElMessage.warning('CSV 至少需要一行表头与一行数据')
    return
  }
  const headers = matrix[0].map((h) => h.replace(/^\uFEFF/, '').trim())
  const iFn = matchCsvHeaderColumn(headers, ['数据字段', 'field_name', '数据字段名称'])
  const iL1 = matchCsvHeaderColumn(headers, ['一级分类标识', 'taxonomy_l1_node_key'])
  const iL2 = matchCsvHeaderColumn(headers, ['二级分类标识', 'taxonomy_l2_node_key'])
  const iLeaf = matchCsvHeaderColumn(headers, ['最细分类标识', 'taxonomy_leaf_node_key', '三级分类标识'])
  const iGr = matchCsvHeaderColumn(headers, ['密级', 'confidentiality_grade'])
  const iNotes = matchCsvHeaderColumn(headers, ['备注', 'notes'])
  if (iFn < 0 || iGr < 0) {
    ElMessage.warning('表头须含「数据字段」「密级」（或 field_name、confidentiality_grade）')
    return
  }
  await loadStructuredGovernanceData()
  await loadFieldCatalog()
  const nodeByKey = new Map(taxonomyNodesAll.value.filter((n) => n.is_active).map((n) => [n.node_key, n]))
  let ok = 0
  const errs: string[] = []
  for (const r of matrix.slice(1)) {
    const fn = (r[iFn] || '').trim()
    if (!fn) continue
    const entry = fieldCatalog.value.find((e) => e.field_name === fn)
    if (!entry) {
      errs.push(`${fn}: 主表中无该字段`)
      continue
    }
    const l1k = iL1 >= 0 ? (r[iL1] || '').trim() : ''
    const l2k = iL2 >= 0 ? (r[iL2] || '').trim() : ''
    const leafk = iLeaf >= 0 ? (r[iLeaf] || '').trim() : ''
    const l1 = l1k ? nodeByKey.get(l1k) : undefined
    const l2 = l2k ? nodeByKey.get(l2k) : undefined
    const leaf = leafk ? nodeByKey.get(leafk) : undefined
    try {
      if (leaf) {
        await toolsApi.upsertDataSecureFieldClassGrade(props.toolId, {
          project_space_id: selectedSpaceId.value,
          catalog_entry_id: entry.id,
          taxonomy_l2_id: leaf.id,
          confidentiality_grade: (r[iGr] || '').trim(),
          notes: iNotes >= 0 ? (r[iNotes] || '').trim() || undefined : undefined,
          change_reason: changeReason
        })
      } else {
        await toolsApi.upsertDataSecureFieldClassGrade(props.toolId, {
          project_space_id: selectedSpaceId.value,
          catalog_entry_id: entry.id,
          taxonomy_l1_id: l1?.id,
          taxonomy_l2_id: l2?.id,
          confidentiality_grade: (r[iGr] || '').trim(),
          notes: iNotes >= 0 ? (r[iNotes] || '').trim() || undefined : undefined,
          change_reason: changeReason
        })
      }
      ok += 1
    } catch (e: any) {
      errs.push(`${fn}: ${e?.message || '失败'}`)
    }
  }
  ElMessage.success(`密级绑定导入完成：成功 ${ok} 条`)
  if (errs.length) await ElMessageBox.alert(errs.slice(0, 30).join('\n'), '部分行未导入', { type: 'warning' })
  await loadStructuredGovernanceData()
}

const onGovernanceClassGradeCsvChange = async (ev: Event) => {
  const target = ev.target as HTMLInputElement
  const file = target.files?.[0]
  target.value = ''
  if (!file || !selectedSpaceId.value) return
  const changeReason = await askChangeReason('密级绑定 CSV 导入')
  if (!changeReason) return
  try {
    const text = await file.text()
    const matrix = parseMatrixFromCsvText(text)
    await importGovernanceClassGradeMatrix(matrix, changeReason)
  } catch (error: any) {
    ElMessage.error(error?.message || '导入失败')
  }
}

const applyGovernanceClassGradeBatchText = async () => {
  if (!selectedSpaceId.value) return ElMessage.warning('请先选择项目空间')
  const matrix = parseMatrixFromCsvText(governanceClassGradeBatchText.value)
  if (matrix.length < 2) {
    ElMessage.warning('至少需要一行表头与一行数据')
    return
  }
  const changeReason = await askChangeReason('密级绑定 文本批量导入')
  if (!changeReason) return
  try {
    await importGovernanceClassGradeMatrix(matrix, changeReason)
    governanceClassGradeBatchText.value = ''
  } catch (error: any) {
    ElMessage.error(error?.message || '导入失败')
  }
}

const importGovernanceSecurityMatrix = async (matrix: string[][], changeReason: string) => {
  if (!selectedSpaceId.value) return
  if (matrix.length < 2) {
    ElMessage.warning('CSV 至少需要一行表头与一行数据')
    return
  }
  const headers = matrix[0].map((h) => h.replace(/^\uFEFF/, '').trim())
  const iFn = matchCsvHeaderColumn(headers, ['数据字段', 'field_name', '数据字段名称'])
  const iReq = matchCsvHeaderColumn(headers, ['要求摘要', '安全要求说明', 'requirement_text'])
  const iExpr = matchCsvHeaderColumn(headers, ['逻辑表达式', 'logic_expression'])
  const iPred = matchCsvHeaderColumn(headers, ['谓词JSON', '谓词', 'predicate_json'])
  const iPri = matchCsvHeaderColumn(headers, ['优先级', 'priority'])
  const iSort = matchCsvHeaderColumn(headers, ['排序', 'sort_order'])
  if (iFn < 0 || iReq < 0 || iExpr < 0 || iPred < 0) {
    ElMessage.warning('表头须含「数据字段」「要求摘要」「逻辑表达式」「谓词JSON」及对应英文列名亦可')
    return
  }
  await loadFieldCatalog()
  let ok = 0
  const errs: string[] = []
  for (const r of matrix.slice(1)) {
    const fn = (r[iFn] || '').trim()
    if (!fn) continue
    const entry = fieldCatalog.value.find((e) => e.field_name === fn)
    if (!entry) {
      errs.push(`${fn}: 主表中无该字段`)
      continue
    }
    let pred: Record<string, unknown> = {}
    try {
      pred = JSON.parse((r[iPred] || '').trim() || '{}') as Record<string, unknown>
    } catch {
      errs.push(`${fn}: predicate_json 非合法 JSON`)
      continue
    }
    try {
      await toolsApi.createDataSecureFieldSecurityRequirement(props.toolId, {
        project_space_id: selectedSpaceId.value,
        catalog_entry_id: entry.id,
        requirement_text: (r[iReq] || '').trim(),
        logic_expression: (r[iExpr] || '').trim(),
        predicate_map: pred,
        priority: iPri >= 0 ? Number(r[iPri]) || 100 : 100,
        sort_order: iSort >= 0 ? Number(r[iSort]) || 0 : 0,
        change_reason: changeReason
      })
      ok += 1
    } catch (e: any) {
      errs.push(`${fn}: ${e?.message || '失败'}`)
    }
  }
  ElMessage.success(`安全要求导入完成：成功 ${ok} 条`)
  if (errs.length) await ElMessageBox.alert(errs.slice(0, 30).join('\n'), '部分行未导入', { type: 'warning' })
  await loadStructuredGovernanceData()
}

const onGovernanceSecurityCsvChange = async (ev: Event) => {
  const target = ev.target as HTMLInputElement
  const file = target.files?.[0]
  target.value = ''
  if (!file || !selectedSpaceId.value) return
  const changeReason = await askChangeReason('安全要求 CSV 导入')
  if (!changeReason) return
  try {
    const text = await file.text()
    const matrix = parseMatrixFromCsvText(text)
    await importGovernanceSecurityMatrix(matrix, changeReason)
  } catch (error: any) {
    ElMessage.error(error?.message || '导入失败')
  }
}

const applyGovernanceSecurityBatchText = async () => {
  if (!selectedSpaceId.value) return ElMessage.warning('请先选择项目空间')
  const matrix = parseMatrixFromCsvText(governanceSecurityBatchText.value)
  if (matrix.length < 2) {
    ElMessage.warning('至少需要一行表头与一行数据')
    return
  }
  const changeReason = await askChangeReason('安全要求 文本批量导入')
  if (!changeReason) return
  try {
    await importGovernanceSecurityMatrix(matrix, changeReason)
    governanceSecurityBatchText.value = ''
  } catch (error: any) {
    ElMessage.error(error?.message || '导入失败')
  }
}

const exportUsageReports = async () => {
  const res = await toolsApi.exportDataSecureFieldUsageReports(props.toolId, recordSpaceId.value ?? selectedSpaceId.value ?? undefined)
  downloadFieldUsageExportCsv(`data-secure-field-usage-${Date.now()}.csv`, res.items)
  ElMessage.success('已导出字段填报记录')
}

const loadAll = async () => {
  loading.value = true
  loadError.value = ''
  try {
    await loadSpaces()
    if (tab.value === 'questionnaire' && selectedSpaceId.value) {
      await loadQuestionnaireData()
    } else if (tab.value === 'field-governance' && selectedSpaceId.value) {
      await loadFieldGovernanceData()
    } else if (tab.value === 'records') {
      await loadRecordsPaneData()
    } else if (tab.value === 'classification-governance' && selectedSpaceId.value) {
      await loadStructuredGovernanceData()
    } else if (tab.value === 'change-logs' && selectedSpaceId.value) {
      await loadGovernanceChangeLogs()
    }
  } catch (error: any) {
    loadError.value = error.message || '加载治理数据失败'
    ElMessage.error(loadError.value)
  } finally {
    loading.value = false
  }
}
onMounted(() => {
  void loadAll()
})
</script>

<style scoped>
.data-secure-manage-manage-tab { display: flex; flex-direction: column; gap: 16px; }
.section-hint { color: #606266; font-size: 13px; margin: 0 0 12px; }
.inline-form { margin-bottom: 12px; }
.table-pagination { margin-top: 12px; display: flex; justify-content: flex-end; }
.expr-builder-card { margin-bottom: 10px; }
.expr-builder-row { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 10px; }
.question-keys-wrap { margin-bottom: 6px; }
.question-key-tag { cursor: pointer; }
.expr-alert { margin-bottom: 8px; }
.section-alert { margin-bottom: 12px; }
.catalog-toolbar { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 12px; align-items: center; }
.catalog-csv-input { display: none; }
.governance-csv-toolbar .toolbar-label { font-size: 13px; color: #606266; margin-right: 6px; }
.governance-batch-text-form { margin-bottom: 16px; max-width: 920px; }
.governance-batch-text-form :deep(.el-textarea) { margin-bottom: 8px; }
.workbench-batch-card { margin-bottom: 16px; max-width: 920px; }
.sec-pred-add { margin: 8px 0 12px; }
.sec-pred-table { margin-bottom: 4px; }
.section-card { margin-bottom: 12px; }

.ds-manage-inner-tabs :deep(.el-tabs__content) {
  padding-top: 8px;
}
</style>
