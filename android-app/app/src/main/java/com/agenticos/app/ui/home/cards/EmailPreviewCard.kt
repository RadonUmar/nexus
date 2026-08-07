package com.agenticos.app.ui.home.cards

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Close
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.agenticos.app.ui.theme.AgenticBlack
import com.agenticos.app.ui.theme.AgenticBlue
import com.agenticos.app.ui.theme.AgenticStroke
import com.agenticos.app.ui.theme.AgenticSurface
import com.agenticos.app.ui.theme.AgenticSurfaceRaised
import com.agenticos.app.ui.theme.AgenticTextPrimary
import com.agenticos.app.ui.theme.AgenticTextSecondary
import com.agenticos.app.ui.theme.AgenticTextTertiary
import com.agenticos.app.ui.theme.AgenticVoid

data class MockEmail(
    val sender: String,
    val subject: String,
    val preview: String,
    val body: String,
    val timestamp: String,
)

/**
 * Placeholder mail surface — mocked data for now (see README on required
 * OPENAI_API_KEY / backend wiring). Stands in for the eventual pattern where the
 * agent renders whatever the user asked to see (a specific email, a thread, a
 * search result) as a structured card instead of raw chat text.
 */
@Composable
fun EmailPreviewCard(emails: List<MockEmail>, onClose: () -> Unit) {
    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(Brush.verticalGradient(colors = listOf(AgenticVoid, AgenticBlack))),
    ) {
        Column(modifier = Modifier.fillMaxSize().statusBarsPadding()) {
            Row(
                modifier = Modifier.fillMaxWidth().padding(horizontal = 20.dp, vertical = 12.dp),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.SpaceBetween,
            ) {
                Text(
                    text = "mail",
                    color = AgenticTextPrimary,
                    fontSize = 22.sp,
                    fontWeight = FontWeight.Light,
                )
                IconButton(onClick = onClose) {
                    Icon(imageVector = Icons.Filled.Close, contentDescription = "Close", tint = AgenticTextSecondary)
                }
            }

            LazyColumn(
                modifier = Modifier.fillMaxSize(),
                contentPadding = androidx.compose.foundation.layout.PaddingValues(horizontal = 20.dp, vertical = 8.dp),
            ) {
                items(emails) { email -> EmailRow(email) }
            }
        }
    }
}

@Composable
private fun EmailRow(email: MockEmail) {
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(20.dp))
            .background(AgenticSurface)
            .padding(18.dp),
    ) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Box(
                modifier = Modifier
                    .size(40.dp)
                    .clip(CircleShape)
                    .background(AgenticSurfaceRaised),
                contentAlignment = Alignment.Center,
            ) {
                Text(
                    text = email.sender.take(1),
                    color = AgenticBlue,
                    fontSize = 16.sp,
                    fontWeight = FontWeight.Medium,
                )
            }
            Spacer(modifier = Modifier.width(12.dp))
            Column(modifier = Modifier.weight(1f)) {
                Text(email.sender, color = AgenticTextPrimary, fontSize = 15.sp, fontWeight = FontWeight.Medium)
                Text(email.subject, color = AgenticTextPrimary, fontSize = 14.sp, fontWeight = FontWeight.Normal)
            }
            Text(email.timestamp, color = AgenticTextTertiary, fontSize = 12.sp)
        }

        Spacer(modifier = Modifier.height(10.dp))

        Box(modifier = Modifier.fillMaxWidth().height(1.dp).background(AgenticStroke.copy(alpha = 0.5f)))

        Spacer(modifier = Modifier.height(10.dp))

        Text(email.body, color = AgenticTextSecondary, fontSize = 14.sp, lineHeight = 20.sp)
    }
}
