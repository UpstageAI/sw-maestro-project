import { FormEvent, useEffect, useState } from "react";
import {
  AuthPayload,
  AuthResponse,
  User,
  getCurrentUser,
  login,
  register
} from "./api/auth";
import { Child, ChildCreatePayload, createChild } from "./api/children";
import {
  StoryGeneratePayload,
  StoryGenerateResponse,
  generateStory
} from "./api/stories";

const ACCESS_TOKEN_KEY = "fairytale.accessToken";

type AuthMode = "login" | "register";
type AppPage = "home" | "story" | "mypage";

type AuthFormState = AuthPayload & {
  confirmPassword: string;
};

type ChildFormState = {
  name: string;
  age: string;
  personality: string;
  favorite_character: string;
  favorite_toy: string;
  family_relationship: string;
};

type StoryFormState = StoryGeneratePayload;

const initialAuthForm: AuthFormState = {
  email: "",
  password: "",
  confirmPassword: ""
};

const initialChildForm: ChildFormState = {
  name: "",
  age: "",
  personality: "",
  favorite_character: "",
  favorite_toy: "",
  family_relationship: ""
};

const initialStoryForm: StoryFormState = {
  child_id: "",
  situation: "",
  lesson: "",
  mood: "따뜻한",
  category: "모험"
};

function App() {
  const [mode, setMode] = useState<AuthMode>("login");
  const [page, setPage] = useState<AppPage>("home");
  const [authForm, setAuthForm] = useState<AuthFormState>(initialAuthForm);
  const [childForm, setChildForm] = useState<ChildFormState>(initialChildForm);
  const [storyForm, setStoryForm] = useState<StoryFormState>(initialStoryForm);
  const [user, setUser] = useState<User | null>(null);
  const [child, setChild] = useState<Child | null>(null);
  const [story, setStory] = useState<StoryGenerateResponse | null>(null);
  const [accessToken, setAccessToken] = useState<string | null>(() =>
    localStorage.getItem(ACCESS_TOKEN_KEY)
  );
  const [isAuthSubmitting, setIsAuthSubmitting] = useState(false);
  const [isChildSubmitting, setIsChildSubmitting] = useState(false);
  const [isStorySubmitting, setIsStorySubmitting] = useState(false);
  const [isRestoring, setIsRestoring] = useState(Boolean(accessToken));
  const [authMessage, setAuthMessage] = useState<string | null>(null);
  const [authError, setAuthError] = useState<string | null>(null);
  const [childMessage, setChildMessage] = useState<string | null>(null);
  const [childError, setChildError] = useState<string | null>(null);
  const [storyMessage, setStoryMessage] = useState<string | null>(null);
  const [storyError, setStoryError] = useState<string | null>(null);

  useEffect(() => {
    if (!accessToken) {
      setIsRestoring(false);
      return;
    }

    getCurrentUser(accessToken)
      .then((currentUser) => {
        setUser(currentUser);
        setPage("home");
      })
      .catch(() => {
        localStorage.removeItem(ACCESS_TOKEN_KEY);
        setAccessToken(null);
      })
      .finally(() => {
        setIsRestoring(false);
      });
  }, [accessToken]);

  const handleAuthSuccess = (response: AuthResponse) => {
    localStorage.setItem(ACCESS_TOKEN_KEY, response.access_token);
    setAccessToken(response.access_token);
    setUser(response.user);
    setPage("home");
    setAuthForm(initialAuthForm);
    setAuthError(null);
    setAuthMessage(
      mode === "register" ? "회원가입이 완료되었습니다." : "로그인되었습니다."
    );
  };

  const handleAuthSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setAuthError(null);
    setAuthMessage(null);

    if (authForm.password.length < 8) {
      setAuthError("비밀번호는 8자 이상이어야 합니다.");
      return;
    }

    if (mode === "register" && authForm.password !== authForm.confirmPassword) {
      setAuthError("비밀번호 확인이 일치하지 않습니다.");
      return;
    }

    setIsAuthSubmitting(true);

    try {
      const payload: AuthPayload = {
        email: authForm.email.trim(),
        password: authForm.password
      };
      const response =
        mode === "register" ? await register(payload) : await login(payload);

      handleAuthSuccess(response);
    } catch (caught: unknown) {
      setAuthError(
        caught instanceof Error ? caught.message : "인증 요청에 실패했습니다."
      );
    } finally {
      setIsAuthSubmitting(false);
    }
  };

  const handleChildSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setChildError(null);
    setChildMessage(null);

    const age = Number(childForm.age);

    if (!Number.isInteger(age) || age < 0 || age > 18) {
      setChildError("나이는 0세부터 18세까지 입력할 수 있습니다.");
      return;
    }

    if (!accessToken) {
      setChildError("로그인이 필요합니다.");
      return;
    }

    const payload: ChildCreatePayload = {
      name: childForm.name.trim(),
      age,
      personality: childForm.personality.trim(),
      favorite_character: childForm.favorite_character.trim(),
      favorite_toy: childForm.favorite_toy.trim(),
      family_relationship: childForm.family_relationship.trim()
    };

    setIsChildSubmitting(true);

    try {
      const createdChild = await createChild(payload, accessToken);
      setChild(createdChild);
      setStoryForm((current) => ({ ...current, child_id: createdChild.id }));
      setChildForm(initialChildForm);
      setChildMessage(`${createdChild.name} 정보가 저장되었습니다. 동화 생성에 사용할 아이 ID가 자동 입력됩니다.`);
    } catch (caught: unknown) {
      setChildError(
        caught instanceof Error ? caught.message : "자녀 정보 저장에 실패했습니다."
      );
    } finally {
      setIsChildSubmitting(false);
    }
  };

  const handleStorySubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setStoryError(null);
    setStoryMessage(null);
    setStory(null);

    if (!accessToken) {
      setStoryError("로그인이 필요합니다.");
      return;
    }

    const payload: StoryGeneratePayload = {
      child_id: storyForm.child_id.trim(),
      situation: storyForm.situation.trim(),
      lesson: storyForm.lesson.trim(),
      mood: storyForm.mood,
      category: storyForm.category
    };

    setIsStorySubmitting(true);

    try {
      const generatedStory = await generateStory(payload, accessToken);
      setStory(generatedStory);
      setStoryMessage("동화가 생성되었습니다.");
    } catch (caught: unknown) {
      setStoryError(
        caught instanceof Error ? caught.message : "동화 생성에 실패했습니다."
      );
    } finally {
      setIsStorySubmitting(false);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem(ACCESS_TOKEN_KEY);
    setAccessToken(null);
    setUser(null);
    setChild(null);
    setStory(null);
    setPage("home");
    setAuthMessage("로그아웃되었습니다.");
    setAuthError(null);
    setChildMessage(null);
    setChildError(null);
    setStoryMessage(null);
    setStoryError(null);
  };

  if (isRestoring) {
    return (
      <main className="loading-screen">
        <p>로그인 상태를 확인하는 중입니다.</p>
      </main>
    );
  }

  if (!user) {
    return (
      <main className="auth-screen">
        <section className="auth-copy">
          <p className="eyebrow">Fairytale</p>
          <h1>아이를 위한 맞춤 동화 만들기</h1>
          <p className="summary">
            로그인 후 아이 정보를 저장하고, 백엔드 API에 맞춤 동화 생성을
            요청할 수 있습니다.
          </p>
        </section>

        <section className="auth-panel" aria-label="인증">
          <div className="mode-tabs" role="tablist" aria-label="인증 모드">
            <button
              aria-selected={mode === "login"}
              className={mode === "login" ? "active" : ""}
              role="tab"
              type="button"
              onClick={() => {
                setMode("login");
                setAuthError(null);
                setAuthMessage(null);
              }}
            >
              로그인
            </button>
            <button
              aria-selected={mode === "register"}
              className={mode === "register" ? "active" : ""}
              role="tab"
              type="button"
              onClick={() => {
                setMode("register");
                setAuthError(null);
                setAuthMessage(null);
              }}
            >
              회원가입
            </button>
          </div>

          <form className="auth-form" onSubmit={handleAuthSubmit}>
            <label>
              이메일
              <input
                autoComplete="email"
                name="email"
                required
                type="email"
                value={authForm.email}
                onChange={(event) =>
                  setAuthForm((current) => ({
                    ...current,
                    email: event.target.value
                  }))
                }
              />
            </label>

            <label>
              비밀번호
              <input
                autoComplete={
                  mode === "register" ? "new-password" : "current-password"
                }
                minLength={8}
                name="password"
                required
                type="password"
                value={authForm.password}
                onChange={(event) =>
                  setAuthForm((current) => ({
                    ...current,
                    password: event.target.value
                  }))
                }
              />
            </label>

            {mode === "register" ? (
              <label>
                비밀번호 확인
                <input
                  autoComplete="new-password"
                  minLength={8}
                  name="confirmPassword"
                  required
                  type="password"
                  value={authForm.confirmPassword}
                  onChange={(event) =>
                    setAuthForm((current) => ({
                      ...current,
                      confirmPassword: event.target.value
                    }))
                  }
                />
              </label>
            ) : null}

            {authError ? <p className="error">{authError}</p> : null}
            {authMessage ? <p className="success">{authMessage}</p> : null}

            <button
              className="primary-button"
              disabled={isAuthSubmitting}
              type="submit"
            >
              {isAuthSubmitting
                ? "처리 중"
                : mode === "register"
                  ? "회원가입"
                  : "로그인"}
            </button>
          </form>
        </section>
      </main>
    );
  }

  return (
    <div className="service-app">
      <header className="topbar">
        <button
          className="brand-button"
          type="button"
          onClick={() => setPage("home")}
        >
          Fairytale
        </button>

        <nav className="topnav" aria-label="주요 메뉴">
          <button
            className={page === "home" ? "active" : ""}
            type="button"
            onClick={() => setPage("home")}
          >
            홈
          </button>
          <button
            className={page === "story" ? "active" : ""}
            type="button"
            onClick={() => setPage("story")}
          >
            동화 생성
          </button>
          <button
            className={page === "mypage" ? "active" : ""}
            type="button"
            onClick={() => setPage("mypage")}
          >
            마이페이지
          </button>
        </nav>

        <div className="user-menu">
          <span>{user.email}</span>
          <button className="text-button" type="button" onClick={handleLogout}>
            로그아웃
          </button>
        </div>
      </header>

      {page === "home" ? (
        <main className="service-main">
          <section className="service-hero">
            <p className="eyebrow">Story Studio</p>
            <h1>오늘의 맞춤 동화를 준비하세요</h1>
            <p className="summary">
              자녀 정보를 등록한 뒤 상황, 교훈, 분위기, 카테고리를 선택해
              개인화된 동화 생성을 요청할 수 있습니다.
            </p>
            <div className="hero-actions">
              <button
                className="primary-button"
                type="button"
                onClick={() => setPage("story")}
              >
                {story ? "생성한 동화 보기" : "동화 생성하기"}
              </button>
              <button
                className="secondary-button"
                type="button"
                onClick={() => setPage("mypage")}
              >
                아이 정보 입력
              </button>
            </div>
          </section>

          <section className="dashboard-grid" aria-label="서비스 현황">
            <article className="info-card">
              <p className="card-label">Profile</p>
              <h2>{child ? child.name : "선택된 아이 없음"}</h2>
              <p>
                {child
                  ? `아이 ID ${child.id}를 사용합니다.`
                  : "동화를 생성하기 전에 아이 정보를 먼저 등록하세요."}
              </p>
            </article>
            <article className="info-card">
              <p className="card-label">Story</p>
              <h2>{story ? story.title : "생성 준비 완료"}</h2>
              <p>
                동화 생성 API는 제목, 본문, 교훈, 이미지와 오디오 URL을
                반환합니다.
              </p>
            </article>
            <article className="info-card">
              <p className="card-label">Account</p>
              <h2>{user.email}</h2>
              <p>인증이 필요한 요청에는 백엔드가 요구하는 Bearer 토큰을 포함합니다.</p>
            </article>
          </section>
        </main>
      ) : null}

      {page === "story" ? (
        <main className="service-main">
          <section className="page-heading">
            <p className="eyebrow">Generate</p>
            <h1>동화 생성</h1>
            <p className="summary">
              아이 ID와 동화 조건을 인증이 필요한 stories API로 전송합니다.
            </p>
          </section>

          <section className="story-layout">
            <form className="story-form form-panel" onSubmit={handleStorySubmit}>
              <label>
                아이 ID
                <input
                  autoComplete="off"
                  name="childId"
                  placeholder="아이 정보를 저장하면 자동으로 입력됩니다"
                  required
                  type="text"
                  value={storyForm.child_id}
                  onChange={(event) =>
                    setStoryForm((current) => ({
                      ...current,
                      child_id: event.target.value
                    }))
                  }
                />
              </label>

              <label>
                상황
                <textarea
                  name="situation"
                  placeholder="예: 유치원 발표를 앞두고 긴장하고 있어요"
                  required
                  rows={4}
                  value={storyForm.situation}
                  onChange={(event) =>
                    setStoryForm((current) => ({
                      ...current,
                      situation: event.target.value
                    }))
                  }
                />
              </label>

              <label>
                교훈
                <input
                  autoComplete="off"
                  name="lesson"
                  placeholder="예: 실수해도 다시 도전하기"
                  required
                  type="text"
                  value={storyForm.lesson}
                  onChange={(event) =>
                    setStoryForm((current) => ({
                      ...current,
                      lesson: event.target.value
                    }))
                  }
                />
              </label>

              <div className="form-grid">
                <label>
                  분위기
                  <select
                    name="mood"
                    value={storyForm.mood}
                    onChange={(event) =>
                      setStoryForm((current) => ({
                        ...current,
                        mood: event.target.value
                      }))
                    }
                  >
                    <option value="따뜻한">따뜻한</option>
                    <option value="신나는">신나는</option>
                    <option value="차분한">차분한</option>
                    <option value="용감한">용감한</option>
                  </select>
                </label>

                <label>
                  카테고리
                  <select
                    name="category"
                    value={storyForm.category}
                    onChange={(event) =>
                      setStoryForm((current) => ({
                        ...current,
                        category: event.target.value
                      }))
                    }
                  >
                    <option value="모험">모험</option>
                    <option value="친구">친구</option>
                    <option value="가족">가족</option>
                    <option value="습관">습관</option>
                    <option value="감정">감정</option>
                  </select>
                </label>
              </div>

              {storyError ? <p className="error">{storyError}</p> : null}
              {storyMessage ? <p className="success">{storyMessage}</p> : null}

              <button
                className="primary-button"
                disabled={isStorySubmitting}
                type="submit"
              >
                {isStorySubmitting ? "생성 중" : "동화 생성"}
              </button>
            </form>

            <aside className="preview-panel">
              <p className="card-label">Preview</p>
              <h2>{story ? story.title : `${storyForm.category} 동화`}</h2>
              {story ? (
                <>
                  <p className="preview-excerpt">{story.body}</p>
                  <dl className="preview-list">
                    <div>
                      <dt>교훈</dt>
                      <dd>{story.lesson}</dd>
                    </div>
                    <div>
                      <dt>생성일</dt>
                      <dd>{new Date(story.created_at).toLocaleString()}</dd>
                    </div>
                  </dl>
                </>
              ) : (
                <dl className="preview-list">
                  <div>
                    <dt>분위기</dt>
                    <dd>{storyForm.mood}</dd>
                  </div>
                  <div>
                    <dt>교훈</dt>
                    <dd>{storyForm.lesson || "입력 전"}</dd>
                  </div>
                  <div>
                    <dt>상황</dt>
                    <dd>{storyForm.situation || "입력 전"}</dd>
                  </div>
                </dl>
              )}
            </aside>
          </section>

          {story ? (
            <section className="story-reader" aria-label="생성된 동화">
              <div className="story-reader-heading">
                <p className="eyebrow">Story</p>
                <h2>{story.title}</h2>
                <p>
                  {child ? `${child.name}에게 들려줄 동화입니다.` : "생성된 동화입니다."}
                </p>
              </div>

              {story.image_url ? (
                <img
                  alt={`${story.title} 삽화`}
                  className="story-image"
                  src={story.image_url}
                />
              ) : null}

              <article className="story-body">
                {story.body
                  .split(/\n{2,}/)
                  .map((paragraph) => paragraph.trim())
                  .filter(Boolean)
                  .map((paragraph, index) => (
                    <p key={`${story.id}-${index}`}>{paragraph}</p>
                  ))}
              </article>

              <div className="story-footer">
                <div>
                  <p className="card-label">교훈</p>
                  <p>{story.lesson}</p>
                </div>
                <div>
                  <p className="card-label">생성일</p>
                  <p>{new Date(story.created_at).toLocaleString()}</p>
                </div>
              </div>

              {story.audio_url ? (
                <audio className="story-audio" controls src={story.audio_url}>
                  오디오를 재생할 수 없습니다.
                </audio>
              ) : null}
            </section>
          ) : null}
        </main>
      ) : null}

      {page === "mypage" ? (
        <main className="service-main">
          <section className="page-heading">
            <p className="eyebrow">Profile</p>
            <h1>아이 정보 관리</h1>
            <p className="summary">
              백엔드 children API가 요구하는 아이 정보를 저장합니다.
            </p>
          </section>

          <section className="profile-layout">
            <aside className="profile-summary">
              <p className="card-label">Current child</p>
              <h2>{child ? child.name : "등록된 아이 없음"}</h2>
              <p>
                {child
                  ? `아이 ID ${child.id}가 동화 생성에 사용됩니다.`
                  : "저장 후 반환된 아이 ID가 자동으로 사용됩니다."}
              </p>
            </aside>

            <form className="child-form form-panel" onSubmit={handleChildSubmit}>
              <label>
                아이 이름
                <input
                  autoComplete="off"
                  name="childName"
                  required
                  type="text"
                  value={childForm.name}
                  onChange={(event) =>
                    setChildForm((current) => ({
                      ...current,
                      name: event.target.value
                    }))
                  }
                />
              </label>

              <label>
                나이
                <input
                  inputMode="numeric"
                  max={18}
                  min={0}
                  name="age"
                  required
                  type="number"
                  value={childForm.age}
                  onChange={(event) =>
                    setChildForm((current) => ({
                      ...current,
                      age: event.target.value
                    }))
                  }
                />
              </label>

              <label>
                성격
                <textarea
                  name="personality"
                  placeholder="예: 호기심이 많고 새로운 것을 좋아해요"
                  required
                  rows={4}
                  value={childForm.personality}
                  onChange={(event) =>
                    setChildForm((current) => ({
                      ...current,
                      personality: event.target.value
                    }))
                  }
                />
              </label>

              <label>
                좋아하는 캐릭터
                <input
                  autoComplete="off"
                  name="favoriteCharacter"
                  placeholder="예: 공룡, 로봇, 마법사"
                  required
                  type="text"
                  value={childForm.favorite_character}
                  onChange={(event) =>
                    setChildForm((current) => ({
                      ...current,
                      favorite_character: event.target.value
                    }))
                  }
                />
              </label>

              <label>
                좋아하는 장난감
                <input
                  autoComplete="off"
                  name="favoriteToy"
                  type="text"
                  value={childForm.favorite_toy}
                  onChange={(event) =>
                    setChildForm((current) => ({
                      ...current,
                      favorite_toy: event.target.value
                    }))
                  }
                />
              </label>

              <label>
                가족 관계
                <input
                  autoComplete="off"
                  name="familyRelationship"
                  type="text"
                  value={childForm.family_relationship}
                  onChange={(event) =>
                    setChildForm((current) => ({
                      ...current,
                      family_relationship: event.target.value
                    }))
                  }
                />
              </label>

              {childError ? <p className="error">{childError}</p> : null}
              {childMessage ? <p className="success">{childMessage}</p> : null}

              <button
                className="primary-button"
                disabled={isChildSubmitting}
                type="submit"
              >
                {isChildSubmitting ? "저장 중" : "아이 정보 저장"}
              </button>
            </form>
          </section>
        </main>
      ) : null}
    </div>
  );
}

export default App;
