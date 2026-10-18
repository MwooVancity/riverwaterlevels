// www.riverwaterlevels.com permanently redirects to the apex over https, path and query kept.
export default {
  fetch(request) {
    const u = new URL(request.url);
    return Response.redirect("https://riverwaterlevels.com" + u.pathname + u.search, 301);
  },
};
