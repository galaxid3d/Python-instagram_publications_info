# Получает информацию об аккаунте Instagram только по его логину, получает список всех публикаций и их описание

# вписать в терминале или командной строке (если ещё не установлено)
# pip install httpx jmespath

import json
import httpx
from urllib.parse import quote
import jmespath

INDENTS = 4 # indents count in JSON and console
PAGE_PUBLICATIONS_LIMIT = 3 # how many publications need to be downloaded at once
HTTP_SESSION_TIMEOUT = 300.0 # how long does the http-session in seconds

def parse_post(data):
    """Instagram publication structure"""
    result = jmespath.search("""{
        id: id,
        shortcode: shortcode,
        dimensions: dimensions,
        src: display_url,
        src_attached: edge_sidecar_to_children.edges[].node.display_url,
        has_audio: has_audio,
        video_url: video_url,
        views: video_view_count,
        plays: video_play_count,
        likes: edge_media_preview_like.count,
        location: location.name,
        taken_at: taken_at_timestamp,
        related: edge_web_media_to_related_media.edges[].node.shortcode,
        type: product_type,
        video_duration: video_duration,
        music: clips_music_attribution_info,
        is_video: is_video,
        tagged_users: edge_media_to_tagged_user.edges[].node.user.username,
        captions: edge_media_to_caption.edges[].node.text,
        related_profiles: edge_related_profiles.edges[].node.username,
        comments_count: edge_media_to_parent_comment.count,
        comments_disabled: comments_disabled,
        comments_next_page: edge_media_to_parent_comment.page_info.end_cursor,
        comments: edge_media_to_parent_comment.edges[].node.{
            id: id,
            text: text,
            created_at: created_at,
            owner: owner.username,
            owner_verified: owner.is_verified,
            viewer_has_liked: viewer_has_liked,
            likes: edge_liked_by.count
        }
    }""", data)
    return result

def scrape_user_posts(user_id: str, session: httpx.Client, page_size: int=PAGE_PUBLICATIONS_LIMIT):
    """Scrape all user publications"""
    base_url = "https://www.instagram.com/graphql/query/?query_hash=e769aa130647d2354c40ea6a439bfc08&variables="
    variables = {
        "id": user_id,
        "first": page_size,
        "after": None,
    }
    while True:
        resp = session.get(base_url + quote(json.dumps(variables)))
        data = resp.json()
        posts = data["data"]["user"]["edge_owner_to_timeline_media"]
        for post in posts["edges"]:
            yield parse_post(post["node"])
        page_info = posts["page_info"]
        if not page_info["has_next_page"]:
            break
        if variables["after"] == page_info["end_cursor"]:
            break
        variables["after"] = page_info["end_cursor"]

client = httpx.Client(
    headers={
        # this is internal ID of an instegram backend app. It doesn't change often.
        "x-ig-app-id": "936619743392459",
        # use browser-like features
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
                      "AppleWebKit/537.36 (KHTML, like Gecko)"
                      "Chrome/62.0.3202.94 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9,ru;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept": "*/*",
    }
)

def scrape_user(username: str):
    """Scrape Instagram user's data"""
    result = client.get(
        f"https://i.instagram.com/api/v1/users/web_profile_info/?username={username}",
    )
    data = json.loads(result.content)
    return data["data"]["user"]

def deep_dict_get(_dict: dict, keys: list, default=None):
    """Get value from dict by list-keys"""
    for key in keys:
        if isinstance(_dict, dict):
            _dict = _dict.get(key, default)
        else:
            return default
    return _dict

def print_user_data(_dict: dict, keys: list, description: str, default=None, indents: int=INDENTS):
    """Print description and value by key in dict"""
    user_data = deep_dict_get(_dict, keys, default=default)
    if user_data and user_data not in [False, True]:
        print(f"{' ' * indents}{description}: {user_data}")
    elif user_data in [False, True]:
        result = {False: 'Нет', True: 'Да'}[user_data]
        print(f"{' ' * indents}{description}: {result}")

if __name__ == "__main__":
    user_name = input("Введите алиас необходимого аккаунта Instagram: ")
    publications_count_need = int(input("Введите сколько необходимо вывести последних публикаций: "))

    with httpx.Client(timeout=httpx.Timeout(HTTP_SESSION_TIMEOUT)) as session:
        # The scrape user profile to find the id and other info:
        scrape_data = scrape_user(user_name)
        user_id = scrape_data["id"]

        # Print user info
        print(f"Информация о пользователе {user_name}:")
        print_user_data(scrape_data, ['id'], 'ID')
        print_user_data(scrape_data, ['full_name'], 'Полное имя')
        print_user_data(scrape_data, ['biography'], 'Биография')
        print_user_data(scrape_data, ['external_url'], 'Дополнительная ссылка')
        print_user_data(scrape_data, ['edge_followed_by', 'count'], 'Подписчиков')
        print_user_data(scrape_data, ['edge_follow', 'count'], 'Подписок')
        print_user_data(scrape_data, ['edge_owner_to_timeline_media', 'count'], 'Публикаций')
        print_user_data(scrape_data, ['highlight_reel_count'], 'Закреплённых Reels')
        print_user_data(scrape_data, ['is_business_account'], 'Является бизнес-акаунтом')
        print_user_data(scrape_data, ['is_professional_account'], 'Является профессиональным акаунтом')
        print_user_data(scrape_data, ['is_private'], 'Является приватным акаунтом')
        print_user_data(scrape_data, ['is_verified'], 'Является подтверждённым акаунтом')
        print_user_data(scrape_data, ['profile_pic_url_hd'], 'Фото профиля')

        # Then we can scrape the info from profile's publications
        publications_count = deep_dict_get(scrape_data, ['edge_owner_to_timeline_media', 'count']) # Всего публикаций
        publications_count_len = len(str(publications_count))
        if publications_count:
            print("\n👇 Публикации по дате размещения:👇\n")

            for j, publication in enumerate(scrape_user_posts(user_id, session=session)):
                print('', end=' ' * INDENTS)
                publication_index = str(j + 1).rjust(publications_count_len)
                print(f"Публикация №{publication_index}: "
                      f"[https://www.instagram.com/p/{publication['shortcode']}]:")

                # Text of publication
                if publication['captions']:
                    print(f"{' ' * INDENTS * 2}Текст публикации:")
                    for text in publication['captions']:
                        print(f"{' ' * INDENTS * 3}{text}")

                # URL-picture
                print(f"{' ' * INDENTS * 2}Картинка публикации:")
                print(f"{' ' * INDENTS * 3}{publication['src']}")

                # Attachments in publication
                if publication['src_attached']:
                    # [1:] - т.к. первое вложение это и есть картинка публикации, поэтому его пропускаем
                    for i, publication_attachment in enumerate(publication['src_attached'][1:]):
                        print('', end=' ' * INDENTS * 2)
                        publication_attachment_index = str(i + 1).rjust(publications_count_len)
                        print(f"Вложение №{publication_attachment_index}:"
                              f"[https://www.instagram.com/p/{publication['shortcode']}/?img_index={i + 2}]:")
                        print(f"{' ' * INDENTS * 3}{publication_attachment}")

                publications_count_need -= 1
                if not publications_count_need:
                    break