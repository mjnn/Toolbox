<template>
  <el-table :data="innerRows" border size="small" class="pred-table">
    <el-table-column label="谓词标识" min-width="140">
      <template #default="scope">
        <el-input v-model="scope.row.token" maxlength="64" :placeholder="tokenPlaceholder" />
      </template>
    </el-table-column>
    <el-table-column label="类型" width="200">
      <template #default="scope">
        <el-select v-model="scope.row.kind" style="width: 100%">
          <el-option v-for="op in kindOptions" :key="op.value" :label="op.label" :value="op.value" />
        </el-select>
      </template>
    </el-table-column>
    <el-table-column label="比较值" min-width="180">
      <template #default="scope">
        <slot name="valueEditor" :row="scope.row" :row-index="scope.$index">
          <el-input v-model="scope.row.value" placeholder="比较值" />
        </slot>
      </template>
    </el-table-column>
    <el-table-column label="" width="90" fixed="right">
      <template #default="scope">
        <el-button type="danger" link :disabled="innerRows.length <= minRows" @click="removeRow(scope.$index)">删除</el-button>
      </template>
    </el-table-column>
  </el-table>
  <el-button class="pred-add" size="small" @click="addRow">新增谓词行</el-button>

  <el-form label-position="top" class="inline-form">
    <el-form-item label="逻辑表达式">
      <el-input v-model="innerExpression" type="textarea" :rows="2" :placeholder="expressionPlaceholder" />
    </el-form-item>
  </el-form>
  <el-card shadow="never" class="expr-builder-card">
    <template #header>表达式构建器</template>
    <div class="expr-builder-row">
      <el-button size="small" @click="appendExpressionToken('(')">(</el-button>
      <el-button size="small" @click="appendExpressionToken(')')">)</el-button>
      <el-button size="small" type="primary" plain @click="appendExpressionToken(' and ')">AND</el-button>
      <el-button size="small" type="primary" plain @click="appendExpressionToken(' or ')">OR</el-button>
      <el-button size="small" type="danger" plain @click="innerExpression = ''">清空</el-button>
    </div>
    <div class="expr-builder-row question-keys-wrap">
      <el-tag
        v-for="tok in tokenList"
        :key="tok"
        class="question-key-tag"
        @click="appendExpressionToken(tok)"
      >
        {{ tok }}
      </el-tag>
      <span v-if="!tokenList.length" class="section-hint">请先在上方表格填写至少一个谓词标识。</span>
    </div>
    <el-alert
      :type="expressionValidation.valid ? 'success' : 'warning'"
      :closable="false"
      show-icon
      :title="expressionValidation.message"
      class="expr-alert"
    />
    <div class="section-hint">括号检查：{{ unmatchedParenHint }}</div>
  </el-card>
</template>

<script setup lang="ts">
import { computed } from 'vue'

export interface PredicateEditorRow {
  token: string
  kind: string
  value: string
  field_key?: string
}

interface KindOption { label: string; value: string }

interface Props {
  rows: PredicateEditorRow[]
  expression: string
  kindOptions: KindOption[]
  defaultRow: PredicateEditorRow
  minRows?: number
  tokenPlaceholder?: string
  expressionPlaceholder?: string
}

const props = withDefaults(defineProps<Props>(), {
  minRows: 1,
  tokenPlaceholder: '如 isC2、inL2',
  expressionPlaceholder: '例如：(isC2 and inL2) or isC3'
})

const emit = defineEmits<{
  (e: 'update:rows', value: PredicateEditorRow[]): void
  (e: 'update:expression', value: string): void
}>()

const innerRows = computed({
  get: () => props.rows,
  set: (v) => emit('update:rows', v)
})
const innerExpression = computed({
  get: () => props.expression,
  set: (v) => emit('update:expression', v)
})

const tokenList = computed(() => {
  const seen = new Set<string>()
  const out: string[] = []
  for (const r of innerRows.value) {
    const t = (r.token || '').trim()
    if (!t || seen.has(t)) continue
    seen.add(t)
    out.push(t)
  }
  return out
})
const validKeySet = computed(() => new Set(tokenList.value))

type LocalExprValidation = { valid: boolean; message: string }
const tokenizeExpressionLocal = (expression: string): string[] => {
  const src = expression.trim()
  const tokens: string[] = []
  let i = 0
  while (i < src.length) {
    const ch = src[i]
    if (/\s/.test(ch)) { i += 1; continue }
    if (ch === '(' || ch === ')') { tokens.push(ch); i += 1; continue }
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
    if (token === '(') { ops.push(token); continue }
    if (token === ')') {
      while (ops.length && ops[ops.length - 1] !== '(') output.push(ops.pop() as string)
      if (!ops.length || ops[ops.length - 1] !== '(') return { valid: false, message: '括号不匹配。' }
      ops.pop()
      continue
    }
    if (low === 'and' || low === 'or') {
      while (ops.length && (ops[ops.length - 1] === 'and' || ops[ops.length - 1] === 'or') && precedence[ops[ops.length - 1]] >= precedence[low]) {
        output.push(ops.pop() as string)
      }
      ops.push(low)
      continue
    }
    if (!validKeys.has(token)) return { valid: false, message: `表达式引用了不存在的谓词标识：${token}` }
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
    } else depth += 1
  }
  return depth === 1 ? { valid: true, message: '表达式格式正确。' } : { valid: false, message: '表达式结构不完整。' }
}
const expressionValidation = computed<LocalExprValidation>(() => {
  const expression = (innerExpression.value || '').trim()
  if (!expression) return { valid: false, message: '请填写逻辑表达式。' }
  return validateExpressionLocal(expression, validKeySet.value)
})
const unmatchedParenHint = computed(() => {
  const text = innerExpression.value || ''
  let depth = 0
  for (const ch of text) {
    if (ch === '(') depth += 1
    if (ch === ')') depth -= 1
  }
  if (depth === 0) return '括号已配平'
  if (depth > 0) return `还缺少 ${depth} 个右括号 )`
  return `右括号过多（多出 ${Math.abs(depth)} 个）`
})

const addRow = () => emit('update:rows', [...innerRows.value, { ...props.defaultRow }])
const removeRow = (idx: number) => {
  if (innerRows.value.length <= props.minRows) return
  const next = [...innerRows.value]
  next.splice(idx, 1)
  emit('update:rows', next)
}
const appendExpressionToken = (token: string) => {
  const current = innerExpression.value || ''
  const needsSpace = current.length > 0 && !current.endsWith(' ') && !token.startsWith(' ') && token !== ')' && token !== '('
  innerExpression.value = `${current}${needsSpace ? ' ' : ''}${token}`.trimStart()
}
</script>

<style scoped>
.pred-table { margin-bottom: 4px; }
.pred-add { margin: 8px 0 12px; }
.expr-builder-card { margin-bottom: 10px; }
.expr-builder-row { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 10px; }
.question-keys-wrap { margin-bottom: 6px; }
.question-key-tag { cursor: pointer; }
.expr-alert { margin-bottom: 8px; }
.section-hint { color: #606266; font-size: 13px; margin: 0 0 12px; }
.inline-form { margin-bottom: 12px; }
</style>
