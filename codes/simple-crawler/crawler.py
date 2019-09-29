# coding: utf-8
# python3
# 要安装 requests: pip3 install requests

import requests


class SimpleCrawler:
    def crawl(self, params=None):
        url = "https://www.zhihu.com/api/v4/columns/pythoneer/followers"
        params = {
            "limit": 20,
            "offset": 0,
            "include": "data[*].follower_count, gender, is_followed, is_following"
        }
        headers = {
            "authority": "www.zhihu.com",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/63.0.3239.84 Safari/537.36",
        }
        response = requests.get(url, headers=headers, params=params)
        print("request url: ", response.url)
        print("returned data: ", response.text)

        for follower in response.json().get("data"):
            print(follower)


if __name__ == '__main__':
    SimpleCrawler().crawl()
