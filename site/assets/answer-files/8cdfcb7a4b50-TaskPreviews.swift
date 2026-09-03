import SwiftUI

// MARK: - 预览（#Preview 宏需完整 Xcode 15+ 环境；
//   命令行类型检查使用 TaskPreviewVerification.swift 中的 PreviewProvider 版本）

#Preview("有数据") {
    NavigationStack {
        TaskListView(store: .preview)
    }
}

#Preview("空状态") {
    NavigationStack {
        TaskListView(store: .emptyPreview)
    }
}

#Preview("任务行-未完成") {
    TaskRow(task: TaskItem(title: "示例任务", isCompleted: false)) {}
        .padding()
}

#Preview("任务行-已完成") {
    TaskRow(task: TaskItem(title: "已完成的任务", isCompleted: true)) {}
        .padding()
}

#Preview("汇总卡片") {
    TaskSummaryCard(remaining: 3, completed: 7)
        .padding()
}

#Preview("空状态视图") {
    EmptyTaskView(filter: .all)
        .frame(height: 300)
}
