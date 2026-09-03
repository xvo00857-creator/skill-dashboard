import SwiftUI
import Observation

// MARK: - 数据模型

/// 任务过滤条件
enum TaskFilter: String, CaseIterable, Equatable {
    case all = "全部"
    case active = "未完成"
    case completed = "已完成"
}

/// 单个任务项 —— 使用稳定的 UUID 作为身份标识，
/// 满足 ForEach 不得使用索引/偏移量作为身份的正确性规则。
struct TaskItem: Identifiable, Equatable {
    let id: UUID
    var title: String
    var isCompleted: Bool
    var createdAt: Date

    init(id: UUID = UUID(), title: String, isCompleted: Bool = false, createdAt: Date = .now) {
        self.id = id
        self.title = title
        self.isCompleted = isCompleted
        self.createdAt = createdAt
    }
}

// MARK: - 预览用自包含模拟数据（不依赖网络或磁盘）

extension TaskItem {
    static let samples: [TaskItem] = [
        TaskItem(title: "阅读 SwiftUI 状态管理文档", isCompleted: true),
        TaskItem(title: "实现任务清单组件", isCompleted: false),
        TaskItem(title: "添加响应式布局适配", isCompleted: false),
        TaskItem(title: "编写无障碍标签", isCompleted: false),
        TaskItem(title: "验证编译通过", isCompleted: false)
    ]
}

// MARK: - @Observable 状态存储

@Observable
@MainActor
final class TaskStore {
    var tasks: [TaskItem] = []
    var filter: TaskFilter = .all

    /// 新增任务输入框文本由视图自身持有，不属于 store。
    /// 这里只暴露经过滤后的任务列表，避免在 body 中内联 filter。
    var filteredTasks: [TaskItem] {
        switch filter {
        case .all:       return tasks
        case .active:    return tasks.filter { !$0.isCompleted }
        case .completed: return tasks.filter { $0.isCompleted }
        }
    }

    var remainingCount: Int {
        tasks.filter { !$0.isCompleted }.count
    }

    var completedCount: Int {
        tasks.filter { $0.isCompleted }.count
    }

    // MARK: - 业务操作（逻辑放在 model 中，视图只负责调用）

    func addTask(title: String) {
        let trimmed = title.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return }
        tasks.insert(TaskItem(title: trimmed), at: 0)
    }

    func toggleCompletion(_ task: TaskItem) {
        guard let index = tasks.firstIndex(where: { $0.id == task.id }) else { return }
        tasks[index].isCompleted.toggle()
    }

    func deleteTasks(at offsets: IndexSet) {
        // offsets 对应 filteredTasks 的索引，需映射回 tasks
        let targets = offsets.compactMap { filteredTasks[safe: $0] }
        tasks.removeAll { task in targets.contains { $0.id == task.id } }
    }

    func clearCompleted() {
        tasks.removeAll { $0.isCompleted }
    }

    // MARK: - 预览用工厂方法

    static var preview: TaskStore {
        let store = TaskStore()
        store.tasks = TaskItem.samples
        return store
    }

    static var emptyPreview: TaskStore {
        TaskStore()
    }
}

// MARK: - 安全下标工具

private extension Array {
    subscript(safe index: Index) -> Element? {
        indices.contains(index) ? self[index] : nil
    }
}
