{
  async function rest(endpoint) {
    const response = await fetch(`${window.base_uri}/app/rest/${endpoint}`, {
      headers: {Accept: 'application/json'},
    })
    if (!response.ok) {
      throw new Error(await response.text())
    }
    return response.json()
  }

  async function getRootUrl() {
    const {webUrl} = await rest('server?fields=webUrl')
    return webUrl
  }

  async function getMyId() {
    const {id} = await rest('users/current?fields=id')
    return Number(id)
  }

  async function detect() {
    const [rootUrl, myId] = await Promise.all([getRootUrl(), getMyId()])
    if (myId < 0) {
      return
    }
    window.postMessage({
      type: 'TEAMCITY_URI',
      url: window.base_uri,
      rootUrl,
    })
  }

  if (!/\/login\.html/.test(location.pathname) && window.BS != null && window.base_uri != null) {
    detect()
  }
}
