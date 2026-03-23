package com.agentbus.mobile

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.safeDrawing
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.windowInsetsPadding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Android
import androidx.compose.material.icons.filled.Devices
import androidx.compose.material.icons.filled.Home
import androidx.compose.material.icons.filled.MenuBook
import androidx.compose.material.icons.filled.People
import androidx.compose.material3.AssistChip
import androidx.compose.material3.BottomAppBar
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.navigation.NavDestination.Companion.hasRoute
import androidx.navigation.NavGraph.Companion.findStartDestination
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.currentBackStackEntryAsState
import androidx.navigation.compose.rememberNavController

private const val HOME_ROUTE = "home"
private const val TUTORIAL_ROUTE = "tutorial"
private const val AGENTS_ROUTE = "agents"
private const val WORKER_ROUTE = "worker"

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun AgentBusApp() {
    val navController = rememberNavController()
    val navBackStackEntry by navController.currentBackStackEntryAsState()
    val currentRoute = navBackStackEntry?.destination?.route ?: HOME_ROUTE

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("AgentBus Mobile") },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = MaterialTheme.colorScheme.surface.copy(alpha = 0.88f),
                ),
            )
        },
        bottomBar = {
            NavigationBar {
                BottomDestinations.forEach { destination ->
                    NavigationBarItem(
                        selected = currentRoute == destination.route,
                        onClick = {
                            navController.navigate(destination.route) {
                                popUpTo(navController.graph.findStartDestination().id) {
                                    saveState = true
                                }
                                launchSingleTop = true
                                restoreState = true
                            }
                        },
                        icon = { Icon(destination.icon, contentDescription = destination.label) },
                        label = { Text(destination.label) },
                    )
                }
            }
        },
        containerColor = MaterialTheme.colorScheme.background,
    ) { padding ->
        NavHost(
            navController = navController,
            startDestination = HOME_ROUTE,
            modifier = Modifier
                .padding(padding)
                .windowInsetsPadding(WindowInsets.safeDrawing),
        ) {
            composable(HOME_ROUTE) { HomeScreen() }
            composable(TUTORIAL_ROUTE) { TutorialScreen() }
            composable(AGENTS_ROUTE) { AgentsScreen() }
            composable(WORKER_ROUTE) { WorkerScreen() }
        }
    }
}

private data class BottomDestination(
    val route: String,
    val label: String,
    val icon: androidx.compose.ui.graphics.vector.ImageVector,
)

private val BottomDestinations = listOf(
    BottomDestination(HOME_ROUTE, "Home", Icons.Filled.Home),
    BottomDestination(TUTORIAL_ROUTE, "Guide", Icons.Filled.MenuBook),
    BottomDestination(AGENTS_ROUTE, "Agents", Icons.Filled.People),
    BottomDestination(WORKER_ROUTE, "Worker", Icons.Filled.Devices),
)

@Composable
private fun HomeScreen() {
    val scrollState = rememberScrollState()
    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(scrollState)
            .padding(20.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp),
    ) {
        HeroCard()
        SectionTitle(title = "What AgentBus does", subtitle = "A file-based bus for agent collaboration.")
        FeatureGrid()
        SectionTitle(title = "Quick facts", subtitle = "Designed to stay lightweight and explicit.")
        QuickFactRow(
            listOf(
                "Repo is the source of truth",
                "Agents are registry-driven",
                "Android can run as a local worker host",
            ),
        )
    }
}

@Composable
private fun HeroCard() {
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(28.dp),
        colors = CardDefaults.cardColors(containerColor = Color.Transparent),
    ) {
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .clip(RoundedCornerShape(28.dp))
                .background(
                    Brush.linearGradient(
                        colors = listOf(
                            MaterialTheme.colorScheme.primary.copy(alpha = 0.95f),
                            MaterialTheme.colorScheme.tertiary.copy(alpha = 0.92f),
                            MaterialTheme.colorScheme.secondary.copy(alpha = 0.85f),
                        ),
                    ),
                )
                .padding(24.dp),
        ) {
            Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                Text(
                    text = "AgentBus Mobile",
                    style = MaterialTheme.typography.headlineMedium,
                    fontWeight = FontWeight.Bold,
                    color = MaterialTheme.colorScheme.onPrimary,
                )
                Text(
                    text = "A native Android companion app for the AgentBus protocol, tutorials, and local worker flows.",
                    style = MaterialTheme.typography.bodyLarge,
                    color = MaterialTheme.colorScheme.onPrimary.copy(alpha = 0.9f),
                )
                AssistChip(
                    onClick = { },
                    label = { Text("Native Compose UI") },
                )
            }
        }
    }
}

@Composable
private fun FeatureGrid() {
    Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
        FeatureCard(
            title = "Visual protocol guide",
            body = "See what tasks, results, labels, and route modes mean without opening raw files first.",
        )
        FeatureCard(
            title = "Agent registry view",
            body = "Review Codex, OpenClaw, Android, and any additional agents configured in the repo registry.",
        )
        FeatureCard(
            title = "Local worker mode",
            body = "Use Android or Termux as a lightweight worker host that claims tasks and writes results.",
        )
    }
}

@Composable
private fun FeatureCard(title: String, body: String) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(24.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.6f)),
    ) {
        Column(modifier = Modifier.padding(18.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Text(title, style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.SemiBold)
            Text(body, style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
    }
}

@Composable
private fun SectionTitle(title: String, subtitle: String) {
    Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
        Text(title, style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.SemiBold)
        Text(subtitle, style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
    }
}

@Composable
private fun QuickFactRow(items: List<String>) {
    Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
        items.forEach { item ->
            Card(
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(18.dp),
            ) {
                Text(
                    text = item,
                    modifier = Modifier.padding(16.dp),
                    style = MaterialTheme.typography.bodyMedium,
                )
            }
        }
    }
}

@Composable
private fun TutorialScreen() {
    val scrollState = rememberScrollState()
    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(scrollState)
            .padding(20.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp),
    ) {
        SectionTitle(title = "Tutorial", subtitle = "A guided walkthrough of the AgentBus workflow.")
        TutorialStepCard(
            step = "1",
            title = "Understand the bus",
            body = "The repo is the source of truth. Tasks, results, inbox files, and the agent registry all live in Git.",
        )
        TutorialStepCard(
            step = "2",
            title = "Add an agent",
            body = "Define a handle in agent_bus/config/agents.yaml. Add aliases and capability flags as needed.",
        )
        TutorialStepCard(
            step = "3",
            title = "Write a task",
            body = "Create a task in agent_bus/tasks/<agent>/ with status ready, route_mode, trace_id, and success criteria.",
        )
        TutorialStepCard(
            step = "4",
            title = "Route the work",
            body = "AgentBus can route by @mention, by label, or by local worker loop. The right agent gets the signal.",
        )
        TutorialStepCard(
            step = "5",
            title = "Capture the result",
            body = "The agent writes a result file and updates the task status so the history stays auditable.",
        )
    }
}

@Composable
private fun TutorialStepCard(step: String, title: String, body: String) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(24.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
    ) {
        Column(
            modifier = Modifier.padding(18.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp),
        ) {
            Text(
                text = "Step $step",
                style = MaterialTheme.typography.labelLarge,
                color = MaterialTheme.colorScheme.primary,
            )
            Text(title, style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.SemiBold)
            Text(body, style = MaterialTheme.typography.bodyMedium)
        }
    }
}

@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun AgentsScreen() {
    val agents = listOf(
        AgentCardUi("codex", "Codex", "Primary action agent", listOf("observe", "review", "act", "comment")),
        AgentCardUi("openclaw", "OpenClaw", "Review-first collaboration agent", listOf("observe", "review", "comment")),
        AgentCardUi("android", "Android / Termux", "Local device worker", listOf("observe", "review", "act")),
    )

    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(20.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp),
    ) {
        SectionTitle(title = "Agent registry", subtitle = "Each agent gets a handle, capabilities, and a routing role.")
        agents.forEach { agent ->
            Card(
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(24.dp),
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.75f)),
            ) {
                Column(modifier = Modifier.padding(18.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                    Text(agent.displayName, style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.SemiBold)
                    Text(agent.description, style = MaterialTheme.typography.bodyMedium)
                    FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                        agent.capabilities.forEach { capability ->
                            AssistChip(onClick = { }, label = { Text(capability) })
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun WorkerScreen() {
    val scrollState = rememberScrollState()
    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(scrollState)
            .padding(20.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp),
    ) {
        SectionTitle(title = "Local worker", subtitle = "Run AgentBus on desktop or Android/Termux with minimal overhead.")
        WorkerCard(
            title = "Desktop worker",
            body = "Use the Python CLI to route tasks and inspect the repository on your PC.",
            command = "python -m agentbus worker --agent codex --once",
        )
        WorkerCard(
            title = "Android / Termux worker",
            body = "Use the phone as a local worker host for lightweight device-based tasks.",
            command = "python -m agentbus worker --agent android --once --handler-script scripts/termux_handler.py",
        )
        WorkerCard(
            title = "Release path",
            body = "Once the Android toolchain is set up, build an APK from Android Studio or Gradle.",
            command = "Build > Build APK(s)",
        )
    }
}

@Composable
private fun WorkerCard(title: String, body: String, command: String) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(24.dp),
    ) {
        Column(modifier = Modifier.padding(18.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
            Text(title, style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.SemiBold)
            Text(body, style = MaterialTheme.typography.bodyMedium)
            Surface(
                shape = RoundedCornerShape(16.dp),
                color = MaterialTheme.colorScheme.inverseSurface,
            ) {
                Text(
                    text = command,
                    modifier = Modifier.padding(14.dp),
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.inverseOnSurface,
                )
            }
        }
    }
}

private data class AgentCardUi(
    val handle: String,
    val displayName: String,
    val description: String,
    val capabilities: List<String>,
)
