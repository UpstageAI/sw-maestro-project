import { authHeaders, request } from "./client";

export type MessageResponse = {
  message: string;
};

export type StoryGeneratePayload = {
  child_id: string;
  situation: string;
  lesson: string;
  mood: string;
  category: string;
};

export type StoryGenerateResponse = {
  id: string;
  title: string;
  body: string;
  lesson: string;
  image_url: string | null;
  audio_url: string | null;
  created_at: string;
};

export function generateStory(
  payload: StoryGeneratePayload,
  token: string
): Promise<StoryGenerateResponse> {
  return request<StoryGenerateResponse>("/stories/generate", {
    method: "POST",
    headers: authHeaders(token),
    body: JSON.stringify(payload)
  });
}

export function listStoryHistory(token: string): Promise<MessageResponse> {
  return request<MessageResponse>("/stories", {
    headers: authHeaders(token)
  });
}

export function regenerateStory(
  storyId: string,
  token: string
): Promise<MessageResponse> {
  return request<MessageResponse>(`/stories/${storyId}/regenerate`, {
    method: "POST",
    headers: authHeaders(token)
  });
}
