import { useDispatch } from "react-redux";
import { API_OPTION } from "../utils/constant";
import { addNowPlayingMovies, addPoularMovies } from "../rtk/movieSlice";
import { useEffect } from "react";

const usePopularMovies = () => {
  const dispatch = useDispatch();

  const getPopularMovies = async () => {
    const data = await fetch(
      "https://api.themoviedb.org/3/movie/popular",
      API_OPTION
    );
    const json = await data.json();

    dispatch(addPoularMovies(json.results));
  };  

  useEffect(() => {
    getPopularMovies();
  }, []);
};

export default usePopularMovies

