package com.agenticos.app.agent

import com.squareup.moshi.JsonClass
import com.squareup.moshi.Moshi
import com.squareup.moshi.kotlin.reflect.KotlinJsonAdapterFactory
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

/**
 * Thin client for the FastAPI backend's chat/action-dispatch endpoint.
 * Mirrors the JSON action-routing pattern already used in agentic_os/chat.py.
 */
class AgentClient(
    private val baseUrl: String = BuildConfig.BACKEND_BASE_URL,
) {
    private val client = OkHttpClient()
    private val moshi = Moshi.Builder().add(KotlinJsonAdapterFactory()).build()

    suspend fun sendMessage(message: String): ChatResponse {
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
        return responseAdapter.fromJson(responseBody) ?: ChatResponse()
    }
}
