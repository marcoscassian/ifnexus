// Sistema de login SUAP via JavaScript
// Substitui a funcionalidade de getLoginURL() do client.js

function getSuapLoginURL(authHost, clientID, redirectURI, scope) {
    var authorizationURL = authHost + '/o/authorize/';
    
    var loginUrl = authorizationURL +
        "?response_type=token" +
        "&client_id=" + encodeURIComponent(clientID) +
        "&scope=" + encodeURIComponent(scope) +
        "&redirect_uri=" + encodeURIComponent(redirectURI);
    
    return loginUrl;
}
