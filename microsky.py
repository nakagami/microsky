################################################################################
# MIT License
#
# Copyright (c) 2025 Hajime Nakagami
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
################################################################################
import sys
import json
import requests
import time

__version__ = "0.1.1"


def _requests_get(url, params=None, headers=None):
    def _urlencode(params):
        converted = []
        for k, s in params.items():
            s = str(s)
            v = ""
            for b in s.encode("utf8"):
                if chr(b) in "0123456789abcdefghijklmnopqrstuvxyzABCDEFGHIJKLMNOPQRSTUVWXYZ-._~":
                    v += chr(b)
                else:
                    v += r"%" + hex(b)[2:]
            converted.append(f"{k}={v}")

        return "&".join(converted)

    if sys.implementation.name == "micropython":
        if params:
            url = url.rstrip('?') + '?' + _urlencode(params)
        response = requests.get(url, headers=headers)
    else:
        if params:
            response = requests.get(url, params=params, headers=headers)
        else:
            response = requests.get(url, headers=headers)
    json_response = response.json()
    if "error" in json_response:
        raise ProtocolError(json_response)
    return json_response


def _requests_post(url, data=None, headers=None):
    if data:
        response = requests.post(url, data=data, headers=headers)
    else:
        response = requests.post(url, headers=headers)
    if not response.text:
        return None
    json_response = response.json()
    if "error" in json_response:
        raise ProtocolError(json_response)
    return json_response


class ProtocolError(Exception):
    def __init__(self, json_response):
        self._data = json_response
        super().__init__(f"{self.error}:{self.message}")

    def __getattr__(self, name):
        if name in self._data:
            return self._data[name]
        raise AttributeError(name)


class Session:
    def __init__(self, json, prefix):
        self._data = json
        self.prefix = prefix

    def __getattr__(self, name):
        if name in self._data:
            return self._data[name]
        raise AttributeError(name)

    def __enter__(self):
        return self

    def __exit__(self, exc, value, traceback):
        self.deleteSession()

    def json(self):
        """return creteSession request response.
        """
        return self._data

    def get(self, path: str, params=None, token="accessJwt") -> dict:
        """ HTTP get with parameters and JWT header
        path: url without prefix
        params: HTTP get parameters dict
        token: JWT header key name
        """
        headers = {"Authorization": f"Bearer {self._data[token]}"}
        return _requests_get(self.prefix + path, params, headers)

    def post(self, path:str, data=None, token="accessJwt") -> dict:
        """ HTTP post with parameters and JWT header
        path: url without prefix
        params: HTTP post parameters dict or bytes
        token: JWT header key name
        """
        headers = {
            "Content-Type": "application/json; charset=UTF-8",
            "Authorization": f"Bearer {self._data[token]}",
        }
        if isinstance(data, dict):
            data = json.dumps(data).encode('utf-8')
        return _requests_post(self.prefix + path, data, headers)

    def current_time(self) -> str:
        """get iso format current datetime"""
        t = time.gmtime()
        return f"{t[0]:04}-{t[1]:02}-{t[2]:02}T{t[3]:02}:{t[4]:02}:{t[5]:02}.000Z"

    # See Bluesky HTTP API reference
    # https://docs.bsky.app/docs/category/http-reference

    def getPreferences(self) -> dict:
        "Get private preferences attached to the current account."
        return self.get("app.bsky.actor.getPreferences")

    def getProfile(self, actor:str) -> dict:
        "Get detailed profile view of an actor."
        return self.get("app.bsky.actor.getProfile", {"actor": actor})

    def getProfiles(self, **kwargs) -> dict:
        "Get detailed profile views of multiple actors."
        assert "actors" in kwargs
        return self.get("app.bsky.actor.getProfiles", kwargs)

    def getSuggestions(self) -> dict:
        "Get a list of suggested actors."
        return self.get("app.bsky.actor.getSuggestions")

    def putPreferences(self, preferences: dict) -> dict:
        """Set the private preferences attached to the account.

        >>> session.putPreferences([{
        ...     "$type": "app.bsky.actor.defs#personalDetailsPref",
        ...     "birthDate":"1967-08-11T00:00:00.000Z",
        ... }])
        """
        return self.post("app.bsky.actor.putPreferences", {"preferences": preferences})

    def getActorFeeds(self, **kwargs) -> dict:
        "Get a list of feeds created by the actor."
        assert "actor" in kwargs
        return self.get("app.bsky.feed.getActorFeeds", kwargs)

    def getActorLikes(self, **kwargs) -> dict:
        "Get a list of posts liked by an actor. "
        assert "actor" in kwargs
        return self.get("app.bsky.feed.getActorLikes", kwargs)

    def getAuthorFeed(self, **kwargs) -> dict:
        "Get a view of an actor's 'author feed' (post and reposts by the author)."
        assert "actor" in kwargs
        return self.get("app.bsky.feed.getAuthorFeed", kwargs)

    def getTimeline(self, **kwargs) -> dict:
        "Get a view of the requesting account's home timeline."
        return self.get("app.bsky.feed.getTimeline", kwargs)

    def getListBlocks(self, **kwargs) -> dict:
        "Get mod lists that the requesting account (actor) is blocking. "
        return self.get("app.bsky.graph.getListBlocks", kwargs)

    def getFollowers(self, **kwargs) -> dict:
        "Enumerates accounts which follow a specified account (actor)."
        assert "actor" in kwargs
        return self.get("app.bsky.graph.getFollowers", kwargs)

    def sendPost(self, text:str) -> dict:
        "post"
        params = {
            "repo": self._data["did"],
            "collection": "app.bsky.feed.post",
            "record": {
                "$type": "app.bsky.feed.post",
                "text": text,
                "createdAt": self.current_time(),
            }
        }
        return self.post("com.atproto.repo.createRecord", params)

    def likePost(self, uri: str, cid: str) -> dict:
        "Like"
        params = {
            "repo": self._data["did"],
            "collection": "app.bsky.feed.like",
            "record": {
                "$type": "app.bsky.feed.like",
                "subject": {
                    "uri": uri,
                    "cid": cid,
                    "$type":"com.atproto.repo.strongRef",
                },
                "validate": True,
                "createdAt": self.current_time(),
            }
        }
        return self.post("com.atproto.repo.createRecord", params)

    def rePost(self, uri: str, cid: str) -> dict:
        "Repost"
        params = {
            "repo": self._data["did"],
            "collection": "app.bsky.feed.repost",
            "record": {
                "$type": "app.bsky.feed.repost",
                "subject": {
                    "uri": uri,
                    "cid": cid,
                    "$type":"com.atproto.repo.strongRef",
                },
                "validate": True,
                "createdAt": self.current_time(),
            }
        }
        return self.post("com.atproto.repo.createRecord", params)

    def deletePost(self, uri:str) -> dict:
        "Delete post"
        params = {
            "repo": self._data["did"],
            "collection": "app.bsky.feed.post",
            "rkey": uri,
        }
        return self.post("com.atproto.repo.deleteRecord", params)

    def unlikePost(self, uri) -> dict:
        "Unlike"
        params = {
            "repo": self._data["did"],
            "collection": "app.bsky.feed.like",
            "rkey": uri,
        }
        return self.post("com.atproto.repo.deleteRecord", params)

    def listPosts(self, did, limit=None, cursor=None, reverse=None) -> dict:
        "A list of my posts"
        params = {
            "repo": did,
            "collection": "app.bsky.feed.post",
        }
        if limit is not None:
            params["limit"] = limit
        if cursor is not None:
            params["cursor"] = cursor
        if reverse is not None:
            params["reverse"] = reverse
        return self.get("com.atproto.repo.listRecords", params)

    def deleteSession(self) -> dict:
        return self.post("com.atproto.server.deleteSession", token="refreshJwt")

    def refreshSession(self) -> dict:
        self._data.update(
            self.post("com.atproto.server.refreshSession", token="refreshJwt")
        )


def createSession(identifier: str, password: str, authFactorToken=None, prefix="https://bsky.social/xrpc/") -> Session:
    params = {"identifier": identifier, "password": password}
    if authFactorToken:
        params["authFactorToken"] = authFactorToken
    json_response = _requests_post(
        prefix + "com.atproto.server.createSession",
        json.dumps(params).encode('utf-8'),
        headers={"Content-Type": "application/json; charset=UTF-8"},
    )
    return Session(json_response, prefix)


def getSession(accessJwt: str, refreshJwt: str, prefix="https://bsky.social/xrpc/") -> Session:
    json_response = _requests_get(
        prefix + "com.atproto.server.getSession",
        headers = {"Authorization": f"Bearer {accessJwt}"}
    )
    session = Session(json_response, prefix)
    session._data["accessJwt"] = accessJwt
    session._data["refreshJwt"] = refreshJwt
    return session
