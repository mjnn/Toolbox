// 工具箱配置 - 可以单独放在一个config.js文件中
const toolsConfig = {
    // 基础API地址 - 修改为你的本地FastAPI地址
    // baseApiUrl: ' http://172.28.60.135:5000',
    baseApiUrl: 'http://172.28.53.33:5000',

    // 工具列表 - 后续可以扩展
    tools: [
        {
            id: 'json-formatter',
            name: 'Json格式化',
            description: '格式化Json字符串工具',
            icon: 'fas fa-font',
            endpoint: '/json_formatter'
        },
        {
            id: 'jwt-decoder',
            name: 'JWT解码',
            description: '解码JWToken字符串工具',
            icon: 'fas fa-font',
            endpoint: '/jwt_decoder'
        },
        {
            id: 'hex-to-ascii',
            name: '十六进制到ASCII转换',
            description: '十六进制到ASCII相互转换工具',
            icon: 'fas fa-font',
            endpoint: '/hex_to_ascii'
        },
        {
            id: 'time-stamp-converter',
            name: '时间戳转换',
            description: 'Unix时间戳转换工具',
            icon: 'fas fa-font',
            endpoint: '/time_stamp_converter'
        },
        {
            id: 'uds_nrc_list_check_tool',
            name: 'UDS NRC 含义查询工具',
            description: '用于查询诊断NRC含义',
            icon: 'fas fa-font',
            endpoint: '/uds_nrc_list_check_tool'
        },
        {
            id: 'uat-sp-tool',
            name: 'UAT SP相关工具',
            description: 'UAT SP后台相关操作工具',
            icon: 'fas fa-chart-bar',
            endpoint: '/uat_sp_tool'
        },
        {
            id: 'avc-checkpoint-tool',
            name: '产线过点信息查询工具',
            description: '批量查询车辆产线过点信息工具',
            icon: 'fas fa-chart-bar',
            endpoint: '/check_point'
        },
        {
            id: 'avc-barcode-tool',
            name: '产线条码信息查询工具',
            description: '批量查询车辆产线条码录入信息工具',
            icon: 'fas fa-chart-bar',
            endpoint: '/barcode'
        },
        {
            id: 'avc-prnum-tool',
            name: '产线PR号信息查询工具',
            description: '批量查询车辆产线PR号信息工具',
            icon: 'fas fa-chart-bar',
            endpoint: '/prnum'
        },
        {
            id: 'live-cei-dp-query-tool',
            name: 'LIVE CEI DP数据查询工具',
            description: '查询LIVE CEI DP车辆数据工具（如CEI RP）',
            icon: 'fas fa-chart-bar',
            endpoint: '/live_cei_dp_query'
        },
        {
            id: 'uat-cei-dp-query-tool',
            name: 'UAT CEI DP数据查询工具',
            description: '查询UAT CEI DP车辆数据工具（如CEI RP）',
            icon: 'fas fa-chart-bar',
            endpoint: '/uat_cei_dp_query'
        },
        {
            id: 'unicom-sim-query-tool',
            name: '联通SIM卡查询工具',
            description: '查询完成SIM卡注册的联通卡信息的工具（该工具请连接外网后再打开）',
            icon: 'fas fa-chart-bar',
            endpoint: '/unicom_sim_query_tool'
        },
        {
            id: 'submit_vehicle_config',
            name: '维护UAT车辆数据工具',
            description: '在UAT环境各个后台维护车辆数据',
            icon: 'fas fa-chart-bar',
            endpoint: '/submit_vehicle_config_tool'
        },
        {
            id: 'uat_sp_project_change',
            name: '切换UAT SP后台车辆所属MOS项目',
            description: '用于在UAT环境切换（一键重新维护）车辆所属MOS项目',
            icon: 'fas fa-chart-bar',
            endpoint: '/uat_sp_project_change_tool'
        },
        {
            id: 'get_signed_iam_x509_cert_tool',
            name: 'AF车 IAM X509证书查询签发解析相关工具',
            description: '用于在UAT环境查询签发解析IAM X509证书',
            icon: 'fas fa-chart-bar',
            endpoint: '/get_signed_iam_x509_cert_tool'
        },
        {
            id: 'get_signed_live_iam_x509_cert_tool',
            name: 'Live环境AF车 IAM X509证书查询签发解析相关工具',
            description: '用于在Live环境查询签发解析IAM X509证书',
            icon: 'fas fa-chart-bar',
            endpoint: '/get_signed_live_iam_x509_cert_tool'
        },
        {
            id: 'search_afc_sim_info_tool',
            name: 'AFC车 电信SIM卡信息查询',
            description: '用于查询AFC项目电信SIM的基本信息（MSISDN等）',
            icon: 'fas fa-chart-bar',
            endpoint: '/search_afc_sim_info_tool'
        },
        {
            id: 'uat_af_dp_data_search_tool',
            name: 'AF车 UAT DP车辆信息查询',
            description: '用于查询AF项目UAT DP车辆信息',
            icon: 'fas fa-chart-bar',
            endpoint: '/uat_af_dp_data_search'
        },
        {
            id: 'uat_vmp_data_search_tool',
            name: 'UAT C车 VMP数据查询工具',
            description: '用于UAT C车 VMP数据查询',
            icon: 'fas fa-chart-bar',
            endpoint: '/uat_vmp_data_search'
        },
        {
            id: 'uat_afc_dp_swap_tool',
            name: 'AFC车 UAT DP换件工具',
            description: '用于AFC车 UAT DP换件',
            icon: 'fas fa-chart-bar',
            endpoint: '/uat_afc_dp_swap'
        },
        {
            id: 'hex_to_800_byte_tool',
            name: 'AF X509证书补齐800字节工具',
            description: '用于AF车  X509证书补齐800字节',
            icon: 'fas fa-chart-bar',
            endpoint: '/hex_to_800_byte_tool'
        }
//        {
//            id: 'image-converter',
//            name: '图片转换',
//            description: '图片格式转换与处理',
//            icon: 'fas fa-image',
//            endpoint: '/tools/image'
//        },
//        {
//            id: 'data-visualizer',
//            name: '数据可视化',
//            description: '创建图表与图形',
//            icon: 'fas fa-chart-bar',
//            endpoint: '/tools/visualize'
//        },
//        {
//            id: 'file-converter',
//            name: '文件转换',
//            description: '多种文件格式转换',
//            icon: 'fas fa-file-export',
//            endpoint: '/tools/file'
//        },
//        {
//            id: 'calculator',
//            name: '高级计算器',
//            description: '科学计算与单位转换',
//            icon: 'fas fa-calculator',
//            endpoint: '/tools/calc'
//        },
//        {
//            id: 'code-formatter',
//            name: '代码格式化',
//            description: '格式化各种编程语言代码',
//            icon: 'fas fa-code',
//            endpoint: '/tools/code'
//        }
    ]
};

// DOM元素
const toolsContainer = document.getElementById('tools-container');
const toolModal = document.getElementById('tool-modal');
const toolFrame = document.getElementById('tool-frame');
const closeBtn = document.querySelector('.close-btn');

// 初始化工具箱
function initToolbox() {
    toolsConfig.tools.forEach(tool => {
        const toolCard = document.createElement('div');
        toolCard.className = 'tool-card';
        toolCard.dataset.toolId = tool.id;
        
        toolCard.innerHTML = `
            <div class="tool-icon">
                <i class="${tool.icon}"></i>
            </div>
            <h3 class="tool-name">${tool.name}</h3>
            <p class="tool-desc">${tool.description}</p>
        `;
        
        toolCard.addEventListener('click', () => openTool(tool));
        toolsContainer.appendChild(toolCard);
    });
}

// 打开工具
function openTool(tool) {
    const toolUrl = `${toolsConfig.baseApiUrl}${tool.endpoint}`;
    toolFrame.src = toolUrl;
    toolModal.style.display = 'block';
    
    // 添加动画类
    document.querySelector('.modal-content').classList.add('modal-open');
}

// 关闭模态框
function closeModal() {
    toolModal.style.display = 'none';
    toolFrame.src = '';
    
    // 移除动画类
    document.querySelector('.modal-content').classList.remove('modal-open');
}

// 点击模态框外部关闭
window.addEventListener('click', (e) => {
    if (e.target === toolModal) {
        closeModal();
    }
});

// 关闭按钮事件
closeBtn.addEventListener('click', closeModal);

// 初始化应用
document.addEventListener('DOMContentLoaded', initToolbox);