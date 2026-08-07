package com.agenticos.app.agent

import com.squareup.moshi.JsonClass
import com.squareup.moshi.Moshi
import com.squareup.moshi.kotlin.reflect.KotlinJsonAdapterFactory
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import com.agenticos.app.BuildConfig

@JsonClass(generateAdapter = true)
data class ChatRequest(
    val message: String,
    val session_id: String = "default",
)

@JsonClass(generateAdapter = true)
data class ChatResponse(
    val response: String? = null,
    val action: String? = null,
    val data: Map<String, Any?>? = null,
)

@JsonClass(generateAdapter = true)
data class DemoCommandRequest(
    val command: String,
    val kind: String? = null,
    val source: String = "phone",
)

/**
 * Thin client for the FastAPI backend's chat/action-dispatch endpoint.
 * Mirrors the JSON action-routing pattern already used in agentic_os/chat.py.
 */
class AgentClient(
    private val baseUrl: String = BuildConfig.BACKEND_BASE_URL,
) {
    private val client = OkHttpClient()
    private val moshi = Moshi.Builder().add(KotlinJsonAdapterFactory()).build()

    suspend fun sendMessage(message: String): ChatResponse = withContext(Dispatchers.IO) {
        val requestAdapter = moshi.adapter(ChatRequest::class.java)
        val responseAdapter = moshi.adapter(ChatResponse::class.java)

        val body = requestAdapter.toJson(ChatRequest(message))
            .toRequestBody("application/json".toMediaType())

        val request = Request.Builder()
            .url("$baseUrl/api/chat")
            .post(body)
            .build()

        val response = client.newCall(request).execute()
        val responseBody = response.body?.string().orEmpty()
        responseAdapter.fromJson(responseBody) ?: ChatResponse()
    }

    suspend fun recordDemoCommand(message: String, kind: String? = null) = withContext(Dispatchers.IO) {
        val requestAdapter = moshi.adapter(DemoCommandRequest::class.java)
        val body = requestAdapter.toJson(DemoCommandRequest(command = message, kind = kind))
            .toRequestBody("application/json".toMediaType())

        val request = Request.Builder()
            .url("$baseUrl/api/demo/commands")
            .post(body)
            .build()

        client.newCall(request).execute().close()
    }
}
