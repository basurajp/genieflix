import { useDispatch } from "react-redux";
import { API_OPTION } from "../utils/constant";
import { addMovietrailer } from "../rtk/movieSlice";
import { useEffect } from "react";

const useTrailerVideo = (moviesId)=>{
    const dispatch = useDispatch();
    // fetchtriler video
    const getMovieVideos = async () => {
      const data = await fetch(
        `https://api.themoviedb.org/3/movie/${moviesId}/videos
    `,
        API_OPTION
      );
  
      const json = await data.json();
  
      const filterData = json.results.filter(
        (video, index) => video.type == "Trailer"
      );
  
      const trailer = filterData.length ? filterData[0] : json.results[0];
  
      dispatch(addMovietrailer(trailer));
    };
  
    useEffect(() => {
      getMovieVideos();
    }, []);
}

export default useTrailerVideo