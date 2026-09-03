import SwiftUI

// MARK: - 主任务列表视图

struct TaskListView: View {
    @State private var store: TaskStore
    @State private var newTaskText = ""
    @Environment(\.horizontalSizeClass) private var horizontalSizeClass

    /// 生产环境默认初始化；预览可注入预置数据的 store。
    init(store: TaskStore? = nil) {
        _store = State(initialValue: store ?? TaskStore())
    }

    var body: some View {
        if horizontalSizeClass == .regular {
            regularWidthLayout
        } else {
            compactWidthLayout
        }
    }

    // MARK: - 宽屏布局（iPad / macOS）：两栏导航

    private var regularWidthLayout: some View {
        NavigationSplitView {
            sidebarContent
                .navigationTitle("任务清单")
                .toolbar { sharedToolbar }
                .navigationSplitViewColumnWidth(min: 240, ideal: 280)
        } detail: {
            detailContent
        }
    }

    // MARK: - 窄屏布局（iPhone）：单栏堆叠

    private var compactWidthLayout: some View {
        NavigationStack {
            VStack(spacing: 16) {
                TaskSummaryCard(remaining: store.remainingCount, completed: store.completedCount)
                    .padding(.horizontal)

                listContent
            }
            .navigationTitle("任务清单")
            .toolbar { sharedToolbar }
        }
    }

    // MARK: - 侧边栏内容（宽屏）

    private var sidebarContent: some View {
        VStack(spacing: 16) {
            AddTaskField(text: $newTaskText) {
                commitNewTask()
            }
            TaskFilterBar(selection: $store.filter)
            listContent
        }
        .padding()
    }

    // MARK: - 详情区（宽屏）

    private var detailContent: some View {
        VStack(spacing: 24) {
            TaskSummaryCard(remaining: store.remainingCount, completed: store.completedCount)
                .padding()

            Text("选择左侧任务进行查看")
                .font(.title3)
                .foregroundStyle(.secondary)
                .frame(maxWidth: .infinity, maxHeight: .infinity)
        }
        .navigationTitle("详情")
    }

    // MARK: - 共享工具栏

    @ToolbarContentBuilder
    private var sharedToolbar: some ToolbarContent {
        ToolbarItem(placement: .primaryAction) {
            Button("清除已完成", systemImage: "trash") {
                withAnimation(.easeInOut(duration: 0.25)) {
                    store.clearCompleted()
                }
            }
            .disabled(store.completedCount == 0)
            .accessibilityLabel("清除所有已完成任务")
        }
    }

    // MARK: - 任务列表（两种布局共用）

    private var listContent: some View {
        Group {
            if store.filteredTasks.isEmpty {
                EmptyTaskView(filter: store.filter)
            } else {
                List {
                    ForEach(store.filteredTasks) { task in
                        TaskRow(task: task) {
                            withAnimation(.spring(response: 0.3, dampingFraction: 0.7)) {
                                store.toggleCompletion(task)
                            }
                        }
                    }
                    .onDelete(perform: store.deleteTasks)
                }
                #if os(iOS)
                .listStyle(.insetGrouped)
                #else
                .listStyle(.sidebar)
                #endif
            }
        }
    }

    // MARK: - 操作

    private func commitNewTask() {
        let trimmed = newTaskText.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return }
        withAnimation(.spring(response: 0.35, dampingFraction: 0.8)) {
            store.addTask(title: trimmed)
        }
        newTaskText = ""
    }
}

// MARK: - 应用入口

@main
struct TaskDemoApp: App {
    var body: some Scene {
        WindowGroup {
            TaskListView()
        }
        .windowResizability(.contentSize)
    }
}
