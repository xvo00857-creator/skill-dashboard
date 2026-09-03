import SwiftUI

// MARK: - 命令行类型检查用预览（PreviewProvider 协议，无需宏插件）
// 在完整 Xcode 中请使用 TaskPreviews.swift 的 #Preview 宏版本。

struct TaskListView_Previews: PreviewProvider {
    static var previews: some View {
        Group {
            NavigationStack {
                TaskListView(store: .preview)
            }
            .previewDisplayName("有数据")

            NavigationStack {
                TaskListView(store: .emptyPreview)
            }
            .previewDisplayName("空状态")
        }
    }
}

struct TaskRow_Previews: PreviewProvider {
    static var previews: some View {
        Group {
            TaskRow(task: TaskItem(title: "示例任务", isCompleted: false)) {}
                .previewDisplayName("未完成")
            TaskRow(task: TaskItem(title: "已完成的任务", isCompleted: true)) {}
                .previewDisplayName("已完成")
        }
        .padding()
    }
}

struct TaskSummaryCard_Previews: PreviewProvider {
    static var previews: some View {
        TaskSummaryCard(remaining: 3, completed: 7)
            .padding()
            .previewDisplayName("汇总卡片")
    }
}

struct EmptyTaskView_Previews: PreviewProvider {
    static var previews: some View {
        EmptyTaskView(filter: .all)
            .frame(height: 300)
            .previewDisplayName("空状态")
    }
}
