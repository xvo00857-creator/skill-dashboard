import SwiftUI

// MARK: - 可复用卡片样式修饰器

private struct CardStyle: ViewModifier {
    func body(content: Content) -> some View {
        content
            .padding(16)
            .background(.regularMaterial, in: .rect(cornerRadius: 12))
    }
}

extension View {
    func cardStyle() -> some View {
        modifier(CardStyle())
    }
}

// MARK: - 单行任务视图（提取为独立 View 类型，收窄失效边界）

struct TaskRow: View {
    let task: TaskItem
    let onToggle: () -> Void

    var body: some View {
        Button(action: onToggle) {
            HStack(spacing: 12) {
                Image(systemName: task.isCompleted ? "checkmark.circle.fill" : "circle")
                    .font(.title3)
                    .foregroundStyle(task.isCompleted ? .green : .secondary)
                    .accessibilityHidden(true)

                Text(task.title)
                    .strikethrough(task.isCompleted, color: .secondary)
                    .foregroundStyle(task.isCompleted ? .secondary : .primary)
                    .frame(maxWidth: .infinity, alignment: .leading)
            }
            .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
        .accessibilityElement(children: .combine)
        .accessibilityLabel(task.title)
        .accessibilityValue(task.isCompleted ? "已完成" : "未完成")
        .accessibilityAddTraits(task.isCompleted ? [.isButton] : [.isButton])
        .padding(.vertical, 4)
    }
}

// MARK: - 过滤栏

struct TaskFilterBar: View {
    @Binding var selection: TaskFilter

    var body: some View {
        Picker("过滤条件", selection: $selection) {
            ForEach(TaskFilter.allCases, id: \.self) { filter in
                Text(filter.rawValue).tag(filter)
            }
        }
        .pickerStyle(.segmented)
    }
}

// MARK: - 汇总卡片

struct TaskSummaryCard: View {
    let remaining: Int
    let completed: Int

    var body: some View {
        // 使用 ViewThatFits 在窄空间下自动切换为紧凑布局
        ViewThatFits {
            HStack(spacing: 24) {
                statView(title: "未完成", count: remaining, color: .orange)
                Divider().frame(height: 32)
                statView(title: "已完成", count: completed, color: .green)
                Divider().frame(height: 32)
                statView(title: "总计", count: remaining + completed, color: .blue)
            }
            HStack(spacing: 16) {
                statView(title: "未完成", count: remaining, color: .orange)
                statView(title: "已完成", count: completed, color: .green)
            }
        }
        .frame(maxWidth: .infinity)
        .cardStyle()
        .accessibilityElement(children: .combine)
        .accessibilityLabel("任务统计：未完成 \(remaining) 项，已完成 \(completed) 项")
    }

    private func statView(title: String, count: Int, color: Color) -> some View {
        VStack(spacing: 4) {
            Text("\(count)")
                .font(.title2).bold()
                .foregroundStyle(color)
            Text(title)
                .font(.caption)
                .foregroundStyle(.secondary)
        }
    }
}

// MARK: - 新增任务输入栏

struct AddTaskField: View {
    @Binding var text: String
    let onSubmit: () -> Void
    @FocusState private var isFocused: Bool

    var body: some View {
        HStack(spacing: 8) {
            TextField("添加新任务…", text: $text)
                .textFieldStyle(.roundedBorder)
                .focused($isFocused)
                .onSubmit(of: .text) {
                    onSubmit()
                }

            Button(action: onSubmit) {
                Image(systemName: "plus.circle.fill")
                    .font(.title2)
            }
            .disabled(text.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
            .accessibilityLabel("添加任务")
        }
    }
}

// MARK: - 空状态视图

struct EmptyTaskView: View {
    let filter: TaskFilter

    var body: some View {
        VStack(spacing: 12) {
            Image(systemName: "tray")
                .font(.system(size: 48))
                .foregroundStyle(.secondary)
            Text(emptyMessage)
                .font(.headline)
                .foregroundStyle(.secondary)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .accessibilityElement(children: .combine)
    }

    private var emptyMessage: String {
        switch filter {
        case .all:       return "还没有任务，添加一个吧"
        case .active:    return "没有未完成的任务"
        case .completed: return "还没有已完成的任务"
        }
    }
}
